from ultralytics import YOLO
import numpy as np
import cv2

# =================================================
# PATH
# =================================================
MODEL_PATH = r"D:\I-Tail\AI-food_production\Appetite-rawmat-2\food_qc_yolo11\seg_model_v1_accuracy\weights\best.pt"

IMAGE_PATH = r"D:\I-Tail\AI-food_production\Appetite-rawmat-2\test\images\APC_0059_jpg.rf.e594f248198f2d1a5b3db26f165efeba.jpg"

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
CLASS_COLORS = {
    0: (0, 255, 0),     # Chicken_Shred
    1: (0, 165, 255),   # Carrot
    2: (255, 0, 0),     # Peas
    3: (0, 0, 255)      # Potato_White
}

# =================================================
# FUNCTIONS
# =================================================
def area_cm2_from_mask(binary_mask, pixel_per_cm):
    pixel_area = np.sum(binary_mask)
    return pixel_area / (pixel_per_cm ** 2)

def estimate_weight(area_cm2, thickness_cm, density):
    volume_cm3 = area_cm2 * thickness_cm
    return volume_cm3 * density

# =================================================
# LOAD MODEL & INFERENCE
# =================================================
model = YOLO(MODEL_PATH)
results = model(IMAGE_PATH)
r = results[0]

# =================================================
# LOAD IMAGE
# =================================================
img = cv2.imread(IMAGE_PATH)
h, w = img.shape[:2]
image_area = h * w
overlay = img.copy()

# =================================================
# EXTRACT YOLO OUTPUT
# =================================================
boxes = r.boxes.xyxy.cpu().numpy()
classes = r.boxes.cls.cpu().numpy().astype(int)
confs = r.boxes.conf.cpu().numpy()
masks = r.masks.data.cpu().numpy() if r.masks is not None else []

# =================================================
# CALCULATE AREA & WEIGHT
# =================================================
area_pixel_per_class = {}
weight_per_class = {}
total_weight = 0

for mask, cls in zip(masks, classes):
    mask = cv2.resize(mask, (w, h))
    binary_mask = (mask > 0.5).astype(np.uint8)

    pixel_area = np.sum(binary_mask)
    area_pixel_per_class.setdefault(cls, 0)
    area_pixel_per_class[cls] += pixel_area

    area_cm2 = area_cm2_from_mask(binary_mask, PIXEL_PER_CM)

    class_name = model.names[cls]
    density = DENSITY_TABLE.get(class_name, 1.0)

    weight = estimate_weight(area_cm2, AVERAGE_THICKNESS, density)

    weight_per_class.setdefault(cls, 0)
    weight_per_class[cls] += weight
    total_weight += weight

    # draw colored mask
    color = CLASS_COLORS.get(cls, (255, 255, 255))
    colored_mask = np.zeros_like(img)
    colored_mask[binary_mask == 1] = color
    overlay = cv2.addWeighted(overlay, 1.0, colored_mask, 0.5, 0)

# =================================================
# DRAW BBOX + LABEL
# =================================================
for box, cls, conf in zip(boxes, classes, confs):
    x1, y1, x2, y2 = map(int, box)
    label = f"{model.names[cls]} {conf:.2f}"

    cv2.rectangle(
        overlay, (x1, y1), (x2, y2),
        CLASS_COLORS.get(cls, (255, 255, 255)), 2
    )
    cv2.putText(
        overlay, label, (x1, y1 - 8),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
        CLASS_COLORS.get(cls, (255, 255, 255)), 2
    )

# =================================================
# BUILD QC REPORT (for overlay)
# =================================================
qc_lines = []
qc_lines.append("===== FOOD QC REPORT =====")

for cls, pixel_area in area_pixel_per_class.items():
    area_percent = (pixel_area / image_area) * 100
    weight = weight_per_class.get(cls, 0)

    qc_lines.append(
        f"{model.names[cls]} | Area: {area_percent:.2f}% | Weight: {weight:.1f} g"
    )

qc_lines.append("--------------------------------")
qc_lines.append(f"TOTAL WEIGHT: {total_weight:.1f} g")

qc_lines.append("===== COMPOSITION RATIO =====")
for cls, weight in weight_per_class.items():
    ratio = (weight / total_weight) * 100 if total_weight > 0 else 0
    qc_lines.append(
        f"{model.names[cls]} : {ratio:.2f}%"
    )

status = "PASS" if 45 <= total_weight <= 50 else "FAIL"
qc_lines.append("--------------------------------")
qc_lines.append(f"QC RESULT : {status}")

# =================================================
# DRAW TEXT OVERLAY
# =================================================
x, y = 20, 30
line_height = 22

# background
overlay_bg = overlay.copy()
cv2.rectangle(
    overlay_bg,
    (10, 10),
    (540, y + line_height * len(qc_lines) + 10),
    (0, 0, 0),
    -1
)
overlay = cv2.addWeighted(overlay_bg, 0.4, overlay, 0.6, 0)

for i, line in enumerate(qc_lines):
    color = (0, 255, 0)
    if "FAIL" in line:
        color = (0, 0, 255)

    cv2.putText(
        overlay,
        line,
        (x, y + i * line_height),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2
    )

# =================================================
# SHOW RESULT
# =================================================
cv2.imshow("Food QC | Segmentation + Weight + Ratio", overlay)
cv2.waitKey(0)
cv2.destroyAllWindows()