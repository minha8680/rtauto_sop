from ultralytics import YOLO

# 스모크 테스트로 학습한 가중치
model = YOLO("runs/detect/runs/helmet_smoke/weights/best.pt")

model.predict(
    source="datasets/helmet_public/test/images",
    save=True,
    project="runs",
    name="predict_test",
    conf=0.25,
)
