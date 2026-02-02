# ===============================
# qc_service.py
# ===============================
# โมดูลสำหรับ:
# - รัน QC ด้วย YOLO Segmentation
# - คำนวณน้ำหนักวัตถุดิบ
# - บันทึกผล QC ลง Supabase
# ===============================

from ultralytics import YOLO
import numpy as np
import cv2
from PIL import Image, ImageOps
import io
from database.supabase import supabase
from datetime import datetime, timezone, timedelta
from database.supabase import supabase

# ===============================
# CONFIG
# ===============================

MODEL_PATH = r"D:\I-Tail\AI-food_production\Appetite-rawmat-2\food_qc_yolo11\seg_model_v1_accuracy\weights\best.pt"

# =================================================
# CALIBRATION (ปรับจากหน้างานจริง)
# =================================================
CAMERA_HEIGHT_CM = 40
PIXEL_PER_CM = 37.2
AVERAGE_THICKNESS = 3

# density (g/cm3)
DENSITY_TABLE = {
    "Chicken_Shred": 1.05,
    "Carrot": 0.95,
    "Peas": 0.90,
    "Potato_White": 1.00
}

# สี mask ต่อ class (BGR)
CLASS_INFO = {
    0: {"name": "Carrot", "bgr": (0, 165, 255), "hex": "#FFA500"},
    1: {"name": "Chicken_Shred", "bgr": (0, 0, 255), "hex": "#FF0000"},
    2: {"name": "Peas", "bgr": (21, 210, 21), "hex": "#15D215"},
    3: {"name": "Potato_White", "bgr": (246, 254, 3), "hex": "#03FEF6"}
}

# ===============================
# Load YOLO model (โหลดครั้งเดียว)
# ===============================

model = YOLO(MODEL_PATH)
print("Model classes:", model.names)

# ===============================
# Utility functions
# ===============================

def area_cm2_from_mask(binary_mask):
    """คำนวณพื้นที่ (cm²) จาก mask"""
    return np.sum(binary_mask) / (PIXEL_PER_CM ** 2)

def estimate_weight(area_cm2, thickness, density):
    """คำนวณน้ำหนัก (gram)"""
    return area_cm2 * thickness * density

# ===============================
# MAIN QC FUNCTION
# ===============================

def run_qc(image_bytes: bytes) -> dict:
    """รัน QC จาก image bytes แล้วคืนผลลัพธ์เป็น dict"""

    pil_img = Image.open(io.BytesIO(image_bytes))
    pil_img = ImageOps.exif_transpose(pil_img)
    pil_img = pil_img.convert("RGB").resize((640, 640), Image.BILINEAR)

    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    overlay = img.copy()

    r = model(img, conf=0.125)[0]

    if r.masks is None:
        return {
            "total_weight": 0,
            "status": "FAIL",
            "items": [],
            "legend": [],
            "overlay_image": None
        }

    total_weight = 0.0
    weight_per_class = {}

    for mask, cls in zip(r.masks.data, r.boxes.cls):
        cls = int(cls)
        info = CLASS_INFO[cls]
        class_name = info["name"]

        mask = cv2.resize(mask.cpu().numpy(), (w, h))
        binary = (mask > 0.5).astype(np.uint8)

        area_cm2 = area_cm2_from_mask(binary)
        density = DENSITY_TABLE.get(class_name, 1.0)
        weight = estimate_weight(area_cm2, AVERAGE_THICKNESS, density)

        weight_per_class[cls] = weight_per_class.get(cls, 0) + weight
        total_weight += weight

        colored = np.zeros_like(img)
        colored[binary == 1] = info["bgr"]
        overlay = cv2.addWeighted(overlay, 1.0, colored, 0.5, 0)

    items = [
        {
            "class": CLASS_INFO[cls]["name"],
            "weight": round(weight, 1),
            "ratio": round(weight / total_weight * 100, 2),
            "color": CLASS_INFO[cls]["hex"]
        }
        for cls, weight in weight_per_class.items()
    ]

    legend = [
        {"class": info["name"], "color": info["hex"]}
        for info in CLASS_INFO.values()
    ]

    qc_min, qc_max = 45, 55
    status = "PASS" if qc_min <= total_weight <= qc_max else "FAIL"

    overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
    overlay_pil = Image.fromarray(overlay_rgb)
    buf = io.BytesIO()
    overlay_pil.save(buf, format="PNG")

    return {
        "total_weight": round(total_weight, 1),
        "status": status,
        "spec": {"min": qc_min, "max": qc_max},
        "items": items,
        "legend": legend,
        "overlay_image": buf.getvalue()
    }

# ===============================
# SAVE RESULT TO SUPABASE
# ===============================

def save_qc_result(image_name: str, result: dict):
    """
    บันทึกผล QC ลง Supabase
    - qc_result (header)
    - qc_item (detail)
    """
    
    # ===============================
    # 1) insert qc_result
    # ===============================
    qc = supabase.table("qc_result").insert({
        "image_name": image_name,
        "total_weight": result["total_weight"],
        "status": result["status"],
        "total_item": len(result["items"]),
    }).execute()

    if not qc.data:
        raise Exception(f"Insert qc_result failed: {qc}")

    qc_row = qc.data[0]

    # ✅ ใช้ id_qc (ตรงกับตารางจริง)
    qc_id = qc_row["id_qc"]

    # ✅ เวลาที่ถูกต้องจาก DB (UTC)
    created_at = qc_row["created_at"]

    # ===============================
    # 2) insert qc_item
    # ===============================
    for item in result["items"]:
        supabase.table("qc_item").insert({
            "qc_id": qc_id,
            "class": item["class"],
            "weight": item["weight"],
            "ratio": item["ratio"],
        }).execute()

    # ✅ ส่งเวลากลับไปให้ main.py
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
            total_weight,
            status,
            created_at,
            qc_item (
                class,
                weight,
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
            "total_weight": r["total_weight"],
            "status": r["status"],
            "created_at": r["created_at"],
            "items": r.get("qc_item", []),
        }
        for r in res.data
    ]
# ===============================
# END
# ===============================