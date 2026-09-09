from ultralytics import YOLO
import cv2

# 헬멧 검출 모델(스모크 테스트 학습분). 범용 테스트로 되돌리려면 "yolov8n.pt"
MODEL_PATH = "runs/detect/runs/helmet_smoke/weights/best.pt"

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

    results = model(frame, verbose=False)
    annotated_frame = results[0].plot()

    cv2.imshow("YOLO Webcam Test", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()