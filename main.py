from ultralytics import YOLO
import cv2

# 사전학습된 경량 모델 (처음 실행 시 자동 다운로드됨)
model = YOLO("yolov8n.pt")

#cap = cv2.VideoCapture(0)  # 0번 웹캠
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Windows DirectShow

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    annotated_frame = results[0].plot()

    cv2.imshow("YOLO Webcam Test", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()