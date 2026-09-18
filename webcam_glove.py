from ultralytics import YOLO
import cv2

# 장갑 착용/미착용 검출 모델 (glove_v1, 베이스라인 — 아직 실물 미검증)
# 담당 카메라는 작업자 바디캠(0.8m 이내 근접)이라, 웹캠 테스트도 손을 카메라에 가깝게 대고 확인할 것.
MODEL_PATH = "models/glove_v1_best.pt"
CONF = 0.25  # confidence 임계값 — 오탐 많으면 올리고, 미탐 많으면 내리기

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
