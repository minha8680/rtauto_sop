"""인원 수 검출 + 추적 (Phase 2) — 웹캠에서 사람을 검출하고 ByteTrack으로 추적.

COCO 사전학습(yolov8n.pt)의 person 클래스를 그대로 사용한다. 학습 불필요.
ByteTrack이 프레임 간에 각 사람에게 ID를 부여해, 순간 미검출로 인한 인원 수
떨림을 흡수한다. 다음 단계에서 "2인 1조" 규칙(인원 수 != 2가 3초 지속 시 위반)을 붙인다.
"""

import time
from collections import Counter, deque

import cv2
from ultralytics import YOLO

MODEL_PATH = "yolov8n.pt"   # COCO 사전학습
PERSON_CLASS = 0            # COCO 기준 person
CONF = 0.4                  # confidence 임계값
IMGSZ = 480                 # 추론 입력 크기 (작을수록 빠름 -> FPS 상승 -> 추적 안정)
TRACKER = "trackers/bytetrack_person.yaml"   # 저FPS용 튜닝된 ByteTrack 설정
SMOOTH_SEC = 0.5           # 인원 수 안정화 창 (이 시간 동안의 최빈값을 표시)

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

prev = time.time()
history = deque()   # (timestamp, raw_count)

while True:
    ret, frame = cap.read()

    if not ret:
        print("카메라 프레임을 읽을 수 없습니다.")
        break

    # ByteTrack 추적. persist=True 로 프레임 간 트랙 상태 유지
    results = model.track(
        frame,
        classes=[PERSON_CLASS],
        conf=CONF,
        imgsz=IMGSZ,
        persist=True,
        tracker=TRACKER,
        verbose=False,
    )
    boxes = results[0].boxes

    # 현재 프레임에서 ID가 부여된 트랙 수 = 원시 인원 수
    ids = [int(b.id) for b in boxes if b.id is not None]
    raw_count = len(ids)

    # 최근 SMOOTH_SEC 동안의 최빈값 = 안정화된 인원 수
    now = time.time()
    history.append((now, raw_count))
    while history and now - history[0][0] > SMOOTH_SEC:
        history.popleft()
    stable_count = Counter(c for _, c in history).most_common(1)[0][0]

    annotated = results[0].plot()   # 박스 + 트랙 ID 표시

    fps = 1.0 / (now - prev) if now > prev else 0.0
    prev = now
    cv2.putText(annotated, f"Persons: {stable_count}  (raw {raw_count})", (12, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    cv2.putText(annotated, f"track IDs: {sorted(ids)}", (12, 66),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
    cv2.putText(annotated, f"{fps:.1f} FPS", (12, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    cv2.imshow("Person Count + Track", annotated)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
