# train_yolo11m_accuracy.py
# YOLOv11m-seg – High Accuracy for Food QC

from ultralytics import YOLO
from pathlib import Path
import multiprocessing
import sys
import torch


# -------------------------------------------------
# Config selector
# -------------------------------------------------
def choose_config_by_vram(vram_mb: int):
    return {
        "model_name": "yolo11m-seg.pt",

        # -------------------------
        # Image / batch
        # -------------------------
        "imgsz": 640 if vram_mb > 6000 else 512,
        "batch": 4 if vram_mb > 6000 else 2,
        "epochs": 250,

        # -------------------------
        # Optimizer (segmentation-friendly)
        # -------------------------
        "optimizer": "AdamW",
        "lr0": 0.0015,              # ↓ ลด LR เพื่อความนิ่ง
        "weight_decay": 0.01,

        # -------------------------
        # Augmentation (VERY IMPORTANT)
        # -------------------------
        "augment": True,
        "mosaic": 0.2,              # ↓ ลดมาก (วัตถุเล็ก)
        "close_mosaic": 10,         # ปิดเร็ว
        "mixup": 0.0,               # ❌ ปิด
        "copy_paste": 0.05,         # เล็กน้อยพอ

        # -------------------------
        # Color aug (พอประมาณ)
        # -------------------------
        "hsv_h": 0.01,
        "hsv_s": 0.4,
        "hsv_v": 0.3,

        # -------------------------
        # Training stability
        # -------------------------
        "cos_lr": True,
        "warmup_epochs": 8,
        "multi_scale": False,       # ❌ ปิด เพื่อ scale คงที่
        "patience": 40,

        # -------------------------
        # Runtime
        # -------------------------
        "workers": 4 if vram_mb > 6000 else 2,
        "pretrained": True,
        "device": 0,
        "half": True,
    }


# -------------------------------------------------
def run_training(dataset_yaml: str, cfg: dict):
    model = YOLO(cfg["model_name"])

    train_kwargs = {
        "data": dataset_yaml,
        "epochs": cfg["epochs"],
        "imgsz": cfg["imgsz"],
        "batch": cfg["batch"],
        "device": cfg["device"],
        "project": "food_qc_yolo11",
        "name": "seg_model_v1_accuracy",
        "workers": cfg["workers"],
        "pretrained": cfg["pretrained"],

        # optimizer
        "optimizer": cfg["optimizer"],
        "lr0": cfg["lr0"],
        "weight_decay": cfg["weight_decay"],

        # augmentation
        "augment": cfg["augment"],
        "mosaic": cfg["mosaic"],
        "close_mosaic": cfg["close_mosaic"],
        "mixup": cfg["mixup"],
        "copy_paste": cfg["copy_paste"],

        # color
        "hsv_h": cfg["hsv_h"],
        "hsv_s": cfg["hsv_s"],
        "hsv_v": cfg["hsv_v"],

        # schedule
        "cos_lr": cfg["cos_lr"],
        "warmup_epochs": cfg["warmup_epochs"],
        "multi_scale": cfg["multi_scale"],
        "patience": cfg["patience"],

        # precision
        "half": cfg["half"],
    }

    return model.train(**train_kwargs)


# -------------------------------------------------
if __name__ == "__main__":
    multiprocessing.freeze_support()

    dataset_yaml = r"C:\\Users\\49553\\Desktop\\AI Rawmat\\datasets\\food_production\\food_production_2\\Appetite-rawmat-2\\data.yaml"
    if not Path(dataset_yaml).exists():
        print("❌ data.yaml not found")
        sys.exit(1)

    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        vram_mb = int(props.total_memory / (1024 ** 2))
        print(f"GPU: {props.name} | VRAM: {vram_mb} MB")

        cfg = choose_config_by_vram(vram_mb)
        run_training(dataset_yaml, cfg)
    else:
        print("CPU mode")
        cfg = choose_config_by_vram(0)
        cfg.update({"device": "cpu", "batch": 1, "workers": 0, "half": False})
        run_training(dataset_yaml, cfg)
