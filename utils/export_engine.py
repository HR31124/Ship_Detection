from ultralytics import YOLO

model = YOLO('') # Đường dẫn models cần chuyển từ .pt -> .engine
 
model.export(format='engine', half=True, device=0, imgsz=640)