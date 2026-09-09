from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="datasets/helmet_public/data.yaml",
    epochs=3,          # 스모크 테스트용. 정상 확인 후 늘리기
    imgsz=416,         # 640 -> 416으로 낮춰 CPU 속도 확보
    batch=4,
    workers=2,
    device="cpu",
    project="runs",
    name="helmet_smoke",
)