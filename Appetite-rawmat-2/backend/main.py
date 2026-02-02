from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import cv2
import io
import threading
import time
from datetime import datetime, timedelta
from PIL import Image, ImageOps

from database.supabase import supabase
from storage.storage import upload_image, get_public_url
from qc_service import run_qc, save_qc_result


app = FastAPI()

# ===============================
# CORS
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# CCTV
# ===============================
CCTV_URL = "rtsp://Admin1:12345678@192.168.1.106:554/stream2"
latest_frame = None
lock = threading.Lock()

# ===============================
# CCTV Background Thread  ✅ (เพิ่มใหม่)
# ===============================
def camera_loop():
    global latest_frame

    while True:
        cap = cv2.VideoCapture(CCTV_URL, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)

        if not cap.isOpened():
            print("❌ Cannot open Tapo CCTV, retrying...")
            time.sleep(5)
            continue

        print("✅ CCTV connected")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ CCTV frame lost, reconnecting...")
                break

            with lock:
                latest_frame = frame.copy()

        cap.release()
        time.sleep(2)


# ===============================
# Start camera on startup ✅ (เพิ่มใหม่)
# ===============================
@app.on_event("startup")
def start_camera():
    threading.Thread(target=camera_loop, daemon=True).start()


# ===============================
# Utils
# ===============================
def preprocess_image(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img = img.resize((640, 640))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def ensure_json_safe(obj):
    if isinstance(obj, dict):
        return {k: ensure_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_safe(v) for v in obj]
    elif isinstance(obj, (bytes, bytearray)):
        return None
    return obj


# ===============================
# CCTV Stream (LIVE) ✏️ แก้
# ===============================
def gen_frames():
    global latest_frame

    while True:
        with lock:
            if latest_frame is None:
                continue
            frame = latest_frame.copy()

        _, buffer = cv2.imencode(".jpg", frame)
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


@app.get("/cctv")
def cctv_stream():
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ===============================
# QC Upload
# ===============================
@app.post("/qc")
async def qc_api(file: UploadFile = File(...)):
    try:
        image_bytes = preprocess_image(await file.read())
        result = run_qc(image_bytes)
        result["status"] = "PASS" if result["status"] in ["Approved", "PASS"] else "FAIL"

        raw_path = upload_image(image_bytes, file.filename, "raw")
        overlay_path = upload_image(
            result["overlay_image"], "overlay.png", "overlay", "image/png"
        )

        result["image_url"] = get_public_url(raw_path)
        result["overlay_url"] = get_public_url(overlay_path)

        result["created_at"] = save_qc_result(raw_path, result)
        return JSONResponse(content=ensure_json_safe(result))

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ===============================
# QC from CCTV ✅ ใช้ได้ทันที
# ===============================
@app.post("/qc/camera")
def qc_from_camera():
    try:
        with lock:
            if latest_frame is None:
                return JSONResponse(
                    status_code=503,
                    content={"error": "Camera not ready"},
                )
            frame = latest_frame.copy()

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame).resize((640, 640))

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

        result = run_qc(image_bytes)
        result["status"] = "PASS" if result["status"] in ["Approved", "PASS"] else "FAIL"

        filename = f"cctv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        raw_path = upload_image(image_bytes, filename, "raw")
        overlay_path = upload_image(
            result["overlay_image"], "overlay.png", "overlay", "image/png"
        )

        result["image_url"] = get_public_url(raw_path)
        result["overlay_url"] = get_public_url(overlay_path)
        result["created_at"] = save_qc_result(raw_path, result)

        return JSONResponse(content=ensure_json_safe(result))

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ===============================
# QC History (เหมือนเดิม)
# ===============================
def calc_date_range(range_type: str, date_str: str):
    base = datetime.fromisoformat(date_str)

    if range_type == "day":
        start = base.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
    elif range_type == "week":
        start = base - timedelta(days=base.weekday())
        start = start.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=7)
    elif range_type == "month":
        start = base.replace(day=1, hour=0, minute=0, second=0)
        end = (start.replace(month=start.month % 12 + 1, year=start.year + (start.month == 12)))
    elif range_type == "year":
        start = base.replace(month=1, day=1, hour=0, minute=0, second=0)
        end = start.replace(year=start.year + 1)
    else:
        raise ValueError("invalid range")

    return start.isoformat(), end.isoformat()


@app.get("/qc/history")
def qc_history(
    range: str | None = Query(None, enum=["day", "week", "month", "year"]),
    date: str | None = Query(None),
):
    query = (
        supabase
        .table("qc_result")
        .select("id_qc, image_name, total_weight, status, created_at")
        .order("created_at", desc=True)
    )

    if range and date:
        start, end = calc_date_range(range, date)
        query = query.gte("created_at", start).lt("created_at", end)

    qc_res = query.execute()
    qc_ids = [r["id_qc"] for r in qc_res.data]

    items_res = (
        supabase
        .table("qc_item")
        .select("qc_id, class, weight, ratio")
        .in_("qc_id", qc_ids)
        .execute()
    )

    item_map = {}
    for i in items_res.data:
        item_map.setdefault(i["qc_id"], []).append(i)

    return [
        {
            **r,
            "items": item_map.get(r["id_qc"], []),
        }
        for r in qc_res.data
    ]
