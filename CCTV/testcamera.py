import cv2
import os
from datetime import datetime

# RTSP URL
rtsp_url = "rtsp://Admin1:12345678@192.168.1.106:554/stream2"

cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

# โฟลเดอร์เก็บรูป
save_dir = "data_carrot"
os.makedirs(save_dir, exist_ok=True)

# สร้าง window
cv2.namedWindow("Tapo C220", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Tapo C220", 720, 640)

img_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame")
        break

    cv2.imshow("Tapo C220", frame)

    key = cv2.waitKey(1) & 0xFF

    # กด s เพื่อบันทึกรูป
    if key == ord('s'):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{save_dir}/img_{timestamp}_{img_count}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Saved: {filename}")
        img_count += 1

    # กด q เพื่อออก
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()