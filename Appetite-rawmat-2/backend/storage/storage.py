# backend/storage/storage.py
from database.supabase import supabase
from datetime import datetime
import uuid

# ===============================
# CONFIG
# ===============================

BUCKET = "qc-images"


def upload_image(
    image_bytes: bytes,
    filename: str,
    folder: str,
    content_type: str = "image/jpeg"
):
    """
    upload รูปเข้า Supabase Storage
    return: path ของไฟล์ใน bucket
    """

    # ===============================
    # สร้างชื่อไฟล์ไม่ให้ซ้ำ
    # ===============================

    ext = filename.split(".")[-1]
    unique_name = (
        f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_"
        f"{uuid.uuid4().hex}.{ext}"
    )

    path = f"{folder}/{unique_name}"

    # ===============================
    # upload เข้า Supabase Storage
    # ===============================

    res = supabase.storage.from_(BUCKET).upload(
        path,
        image_bytes,
        {"content-type": content_type}
    )

    # ===============================
    # error handling (สำคัญมาก)
    # ===============================

    if hasattr(res, "error") and res.error:
        raise Exception(f"Upload failed: {res.error.message}")

    return path


def get_public_url(path: str) -> str:
    """
    ใช้กรณี bucket เป็น public
    frontend เรียกดูรูปได้ทันที
    """
    return supabase.storage.from_(BUCKET).get_public_url(path)


def get_signed_url(path: str, expires: int = 3600) -> str:
    """
    ใช้กรณี bucket เป็น private
    ได้ url ชั่วคราว (default 1 ชั่วโมง)
    """
    res = supabase.storage.from_(BUCKET).create_signed_url(path, expires)

    if "signedURL" not in res:
        raise Exception("Create signed url failed")

    return res["signedURL"]


# ===============================
# QC HISTORY
# ===============================

def get_qc_history(limit: int = 50):
    """
    ดึงประวัติ QC จากตาราง qc_results
    เรียงล่าสุดก่อน
    """
    res = (
        supabase
        .table("qc_results")
        .select(
            "id, image_name, image_url, overlay_url, total_weight, status, created_at"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message)

    return res.data