"""로컬 CPU 스모크 테스트용 학습 스크립트 — 실사용 아님.

실제 학습은 Google Colab (T4 GPU)에서 한다. 이 파일은 helmet_v1 초기에
"학습이 에러 없이 도는지"만 확인하려고 만든 것으로, epochs 3 / imgsz 416 등
설정이 검증용이다. 본 학습 절차는 README.md 7절, 결과는 docs/helmet_v*/ 참고.
"""

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