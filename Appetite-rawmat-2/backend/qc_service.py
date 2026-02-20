# ===============================
# qc_service.py
# ===============================
# โมดูลสำหรับ:
# - รัน QC ด้วย YOLO Segmentation (Triple Model)
# - นับจำนวนวัตถุดิบแทนน้ำหนัก
# - บันทึกผล QC ลง Supabase
# ===============================

from ultralytics import YOLO
import numpy as np
import cv2
from PIL import Image, ImageOps
import io
from database.supabase import supabase

# ===============================
# MODEL CONFIG
# ===============================

MODEL_CONFIGS = {
    "Potato": {
        "path": r"D:\I-Tail\AI-food_production\potato.pt",
        "bgr": (246, 254, 3),
        "hex": "#03FEF6"
    },
    "Peas": {
        "path": r"D:\I-Tail\AI-food_production\peas.pt",
        "bgr": (21, 210, 21),
        "hex": "#15D215"
    },
    "Carrot": {
        "path": r"D:\I-Tail\AI-food_production\carrot.pt",
        "bgr": (0, 165, 255),
        "hex": "#FFA500"
    }
}

# ===============================
# LOAD ALL MODELS (โหลดครั้งเดียว)
# ===============================

models = {}

for name, cfg in MODEL_CONFIGS.items():
    try:
        models[name] = YOLO(cfg["path"])
        print(f"[OK] Loaded model: {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

if not models:
    raise RuntimeError("No YOLO models loaded.")

# ===============================
# MAIN QC FUNCTION
# ===============================

def run_qc(image_bytes: bytes) -> dict:

    pil_img = Image.open(io.BytesIO(image_bytes))
    pil_img = ImageOps.exif_transpose(pil_img)
    # pil_img = pil_img.convert("RGB").resize((640, 640), Image.BILINEAR)
    pil_img = pil_img.convert("RGB")


    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    overlay = img.copy()

    total_count = 0
    count_per_class = {}

    # 🔥 รันทุกโมเดล
    for model_name, model in models.items():

        results = model(img, conf=0.25)[0]

        if results.boxes is None:
            continue

        count = len(results.boxes)

        count_per_class[model_name] = count
        total_count += count

        cfg = MODEL_CONFIGS[model_name]

        # วาดกรอบ
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf_val = float(box.conf[0])

            cv2.rectangle(overlay, (x1, y1), (x2, y2), cfg["bgr"], 2)
            cv2.putText(
                overlay,
                f"{model_name} {conf_val:.2f}",
                (x1, max(y1 - 6, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                cfg["bgr"],
                2
            )

    # ===============================
    # Build Items
    # ===============================

    items = []

    for class_name, count in count_per_class.items():

        ratio = (count / total_count * 100) if total_count > 0 else 0

        items.append({
            "class": class_name,
            "count": count,
            "ratio": round(ratio, 2),
            "color": MODEL_CONFIGS[class_name]["hex"]
        })

    # ===============================
    # QC SPEC (ตัวอย่างตั้งค่า)
    # ===============================

    qc_min, qc_max = 10, 100  # 🔥 ปรับตามหน้างานจริง
    status = "PASS" if qc_min <= total_count <= qc_max else "FAIL"

    # ===============================
    # Convert overlay to bytes
    # ===============================

    overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
    overlay_pil = Image.fromarray(overlay_rgb)
    buf = io.BytesIO()
    overlay_pil.save(buf, format="PNG")

    return {
        "total_count": total_count,
        "status": status,
        "spec": {"min": qc_min, "max": qc_max},
        "items": items,
        "overlay_image": buf.getvalue()
    }

# ===============================
# SAVE RESULT TO SUPABASE
# ===============================

def save_qc_result(image_name: str, result: dict):

    qc = supabase.table("qc_result").insert({
        "image_name": image_name,
        "total_count": result["total_count"],
        "status": result["status"],
        "total_item": len(result["items"]),
    }).execute()

    if not qc.data:
        raise Exception(f"Insert qc_result failed: {qc}")

    qc_row = qc.data[0]
    qc_id = qc_row["id_qc"]
    created_at = qc_row["created_at"]

    for item in result["items"]:
        supabase.table("qc_item").insert({
            "qc_id": qc_id,
            "class": item["class"],
            "count": item["count"],
            "ratio": item["ratio"],
        }).execute()

    return created_at

# ===============================
# GET QC HISTORY
# ===============================

def get_qc_history():

    res = (
        supabase
        .table("qc_result")
        .select("""
            id_qc,
            image_name,
            total_count,
            status,
            created_at,
            qc_item (
                class,
                count,
                ratio
            )
        """)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    return [
        {
            "id_qc": r["id_qc"],
            "image_name": r["image_name"],
            "total_count": r["total_count"],
            "status": r["status"],
            "created_at": r["created_at"],
            "items": r.get("qc_item", []),
        }
        for r in res.data
    ]
