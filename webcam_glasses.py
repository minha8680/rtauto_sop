from ultralytics import YOLO
import cv2

# 보안경 착용/미착용 검출 모델 (glasses_v3). 범용 테스트로 되돌리려면 "yolov8n.pt"
MODEL_PATH = "models/glasses_v3_best.pt"
CONF = 0.20  # confidence 임계값 — 오탐 많으면 올리고, 미탐 많으면 내리기

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        print("카메라 프레임을 읽을 수 없습니다.")
        break

    results = model(frame, conf=CONF, verbose=False)
    annotated_frame = results[0].plot()

    cv2.imshow("YOLO Webcam Test", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
