from roboflow import Roboflow

RF_API_KEY = "eFyXlaz9MOwoHvgnUqLj"

# Connect Roboflow
rf = Roboflow(api_key=RF_API_KEY)

# เลือก workspace + project + version
project = rf.workspace("thanat-9ygau").project("appetite-rawmat")
version = project.version(2)

# ดาวน์โหลด dataset เป็นฟอร์แมต YOLOv11
dataset = version.download("yolov11")    