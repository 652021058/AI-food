from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import cv2
import io
from PIL import Image, ImageOps

from database.supabase import supabase 
from storage.storage import upload_image, get_public_url
from qc_service import run_qc, save_qc_result
from datetime import datetime, timedelta
from fastapi import Query
import threading
import time


app = FastAPI()

# ===============================
# CORS (React Frontend)
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
CCTV_URL = "rtsp://Admin1:12345678@172.20.10.3:554/stream2"
latest_frame = None
lock = threading.Lock()

# ===============================
# Utils
# ===============================
def preprocess_image(image_bytes: bytes) -> bytes:
    """ปรับภาพให้เหมาะกับ AI"""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img = img.resize((640, 640))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def ensure_json_safe(obj):
    """กัน bytes หลุดเข้า JSON response"""
    if isinstance(obj, dict):
        return {k: ensure_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_safe(v) for v in obj]
    elif isinstance(obj, (bytes, bytearray)):
        return None
    else:
        return obj



# ===============================
# CCTV Stream (LIVE)
# ===============================
def gen_frames():
    global latest_frame

    cap = cv2.VideoCapture(CCTV_URL, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("❌ Cannot open Tapo CCTV")
        return

    import time
    time.sleep(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # 🔹 เก็บ frame ล่าสุดไว้ให้ /qc/camera
        with lock:
            latest_frame = frame.copy()

        _, buffer = cv2.imencode(".jpg", frame)
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )

    cap.release()

# ===============================
# ฟังก์ชันคำนวณช่วงเวลา
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
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    
    elif range_type == "year":
        start = base.replace(month=1, day=1, hour=0, minute=0, second=0)
        end = start.replace(year=start.year + 1)

    else:
        raise ValueError("invalid range")

    return start.isoformat(), end.isoformat()



@app.get("/cctv")
def cctv_stream():
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ===============================
# 1) Upload Image + QC + Save
# ===============================
@app.post("/qc")
async def qc_api(file: UploadFile = File(...)):
    try:
        # ===============================
        # 1) อ่าน + preprocess รูป
        # ===============================
        image_bytes = await file.read()
        image_bytes = preprocess_image(image_bytes)

        # ===============================
        # 2) รัน AI QC
        # ===============================
        result = run_qc(image_bytes)
        result["status"] = (
            "PASS" if result["status"] in ["Approved", "PASS"] else "FAIL"
        )

        # ===============================
        # 3) upload รูปเข้า Supabase Storage
        # ===============================

        # 🔹 รูปต้นฉบับ
        raw_path = upload_image(
            image_bytes=image_bytes,
            filename=file.filename,
            folder="raw"
        )
        raw_url = get_public_url(raw_path)

        # 🔹 รูป overlay (มาจาก AI)
        overlay_path = upload_image(
            image_bytes=result["overlay_image"],
            filename="overlay.png",
            folder="overlay",
            content_type="image/png"
        )
        overlay_url = get_public_url(overlay_path)

        # ===============================
        # 4) ใส่ URL กลับเข้า result
        # ===============================
        result["image_url"] = raw_url
        result["overlay_url"] = overlay_url

        # ===============================
        # 5) บันทึกลง Supabase DB
        # ===============================
        created_at = save_qc_result(raw_path, result)
        result["created_at"] = created_at


        # ===============================
        # 6) ส่งกลับ frontend
        # ===============================
        result = ensure_json_safe(result)
        return JSONResponse(content=result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )
    
# ===============================
# 2) Capture จาก CCTV + QC + Save
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

        # ===============================
        # แปลงภาพ
        # ===============================
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame).resize((640, 640))

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        image_bytes = buf.getvalue()

        # ===============================
        # QC
        # ===============================
        result = run_qc(image_bytes)
        result["status"] = (
            "PASS" if result["status"] in ["Approved", "PASS"] else "FAIL"
        )

        # ===============================
        # Upload รูป CCTV → Supabase
        # ===============================
        filename = f"cctv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

        raw_path = upload_image(
            image_bytes=image_bytes,
            filename=filename,
            folder="raw"
        )
        raw_url = get_public_url(raw_path)

        overlay_path = upload_image(
            image_bytes=result["overlay_image"],
            filename="overlay.png",
            folder="overlay",
            content_type="image/png"
        )
        overlay_url = get_public_url(overlay_path)

        # ===============================
        # ใส่ URL กลับ result
        # ===============================
        result["image_url"] = raw_url
        result["overlay_url"] = overlay_url

        # ===============================
        # Save DB
        # ===============================
        created_at = save_qc_result(raw_path, result)
        result["created_at"] = created_at
        
        # ===============================
        # ส่งกลับ frontend
        # ===============================
        result = ensure_json_safe(result)
        return JSONResponse(content=result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


# ===============================
# 3) QChistory
# ===============================
@app.get("/qc/history")
def qc_history(
    range: str | None = Query(None, enum=["day", "week", "month", "year"]),
    date: str | None = Query(None)
):
    query = (
        supabase
        .table("qc_result")
        .select("id_qc, image_name, total_weight, status, created_at")
        .order("created_at", desc=True)
    )

    # ✅ ถ้ามี range + date ค่อย filter
    if range and date:
        start, end = calc_date_range(range, date)
        query = (
            query
            .gte("created_at", start)
            .lt("created_at", end)
        )

    qc_res = query.execute()

    qc_ids = [r["id_qc"] for r in qc_res.data]

    # ดึง qc_item
    items_res = (
        supabase
        .table("qc_item")
        .select("qc_id, class, weight, ratio")
        .in_("qc_id", qc_ids)
        .execute()
    )

    # group qc_item
    item_map = {}
    for i in items_res.data:
        item_map.setdefault(i["qc_id"], []).append(i)

    return [
        {
            "id_qc": r["id_qc"],
            "image_name": r["image_name"],
            "total_weight": r["total_weight"],
            "status": r["status"],
            "created_at": r["created_at"],
            "items": item_map.get(r["id_qc"], []),
        }
        for r in qc_res.data
    ]

# ===============================
# END
# ===============================