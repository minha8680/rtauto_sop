"""인원 수 검출 + 추적 + "2인 1조" 규칙 (Phase 2~3) — 웹캠 미니 데모.

- 검출: COCO 사전학습(yolov8n.pt)의 person 클래스. 학습 불필요.
- 추적: ByteTrack이 프레임 간 ID를 부여해 순간 미검출로 인한 인원 수 떨림을 흡수.
- 규칙: 인원 수 != 2가 3초 이상 지속되면 "2인 1조 위반" 확정. 2명 복귀가
  3초 이상 지속되어야 해제 (기획안 5.6절). 관리자/작업자 확인으로는 해제 불가.

규칙 엔진의 첫 조각. 이후 helmet_v2를 같은 루프에 넣어 사람별 보호구 착용 여부까지 판정.
"""

import time
from collections import Counter, deque

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

MODEL_PATH = "yolov8n.pt"   # COCO 사전학습
PERSON_CLASS = 0            # COCO 기준 person
CONF = 0.4                  # confidence 임계값
IMGSZ = 480                 # 추론 입력 크기 (작을수록 빠름 -> FPS 상승 -> 추적 안정)
TRACKER = "trackers/bytetrack_person.yaml"   # 저FPS용 튜닝된 ByteTrack 설정
SMOOTH_SEC = 0.5           # 인원 수 안정화 창 (이 시간 동안의 최빈값을 표시)

REQUIRED_CREW = 2          # 2인 1조
HOLD_SEC = 3.0             # 위반 확정까지 지속 시간
CLEAR_SEC = 3.0            # 해제까지 정상 복귀 지속 시간

try:
    _FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 22)
    _FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 34)
except OSError:
    _FONT = _FONT_BIG = ImageFont.load_default()


def draw_overlay(bgr, lines, banner_text, banner_rgb):
    """상단 정보 텍스트 + 하단 상태 배너를 한글로 그린다."""
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)
    y = 10
    for text in lines:
        d.text((12, y), text, font=_FONT, fill=(0, 255, 0))
        y += 26
    if banner_text:
        w, h = img.size
        d.rectangle([0, h - 56, w, h], fill=banner_rgb)
        d.text((16, h - 48), banner_text, font=_FONT_BIG, fill=(255, 255, 255))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


class SustainedLatch:
    """조건이 hold_sec 이상 연속 참이면 걸리고(latched),
    거짓이 clear_sec 이상 연속 지속되어야 풀린다. (기획안 5.6절 동작)"""

    def __init__(self, hold_sec, clear_sec):
        self.hold_sec = hold_sec
        self.clear_sec = clear_sec
        self.latched = False
        self.true_since = None
        self.false_since = None
        self.latched_at = None

    def update(self, cond, now):
        if cond:
            self.false_since = None
            if self.true_since is None:
                self.true_since = now
            if not self.latched and now - self.true_since >= self.hold_sec:
                self.latched = True
                self.latched_at = now
        else:
            self.true_since = None
            if self.false_since is None:
                self.false_since = now
            if self.latched and now - self.false_since >= self.clear_sec:
                self.latched = False
                self.latched_at = None
        return self.latched

    def pending(self, now):
        """확정 전 카운트다운 진행률 (0~1). 해당 없으면 None."""
        if not self.latched and self.true_since is not None:
            return min((now - self.true_since) / self.hold_sec, 1.0)
        if self.latched and self.false_since is not None:
            return min((now - self.false_since) / self.clear_sec, 1.0)
        return None


model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

prev = time.time()
history = deque()   # (timestamp, raw_count)
rule = SustainedLatch(HOLD_SEC, CLEAR_SEC)

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

    ids = [int(b.id) for b in boxes if b.id is not None]
    raw_count = len(ids)

    # 최근 SMOOTH_SEC 동안의 최빈값 = 안정화된 인원 수
    now = time.time()
    history.append((now, raw_count))
    while history and now - history[0][0] > SMOOTH_SEC:
        history.popleft()
    stable_count = Counter(c for _, c in history).most_common(1)[0][0]

    # "2인 1조" 규칙
    violation = rule.update(stable_count != REQUIRED_CREW, now)
    pending = rule.pending(now)

    annotated = results[0].plot()   # 박스 + 트랙 ID

    fps = 1.0 / (now - prev) if now > prev else 0.0
    prev = now

    lines = [
        f"인원: {stable_count}명  (raw {raw_count})",
        f"track ID: {sorted(ids)}   {fps:.0f} FPS",
    ]

    if violation:
        elapsed = int(now - rule.latched_at)
        banner = f"2인 1조 위반  ({elapsed}초)"
        if pending is not None:
            banner += f"   해제 대기 {pending * 100:.0f}%"
        annotated = draw_overlay(annotated, lines, banner, (200, 0, 0))
    else:
        if stable_count == REQUIRED_CREW:
            banner = "정상 (2인 1조)"
            rgb = (0, 140, 0)
        else:
            banner = "감시 중"
            rgb = (200, 130, 0)
        if pending is not None:
            banner += f"   위반 감지 {pending * 100:.0f}%"
        annotated = draw_overlay(annotated, lines, banner, rgb)

    cv2.imshow("2인 1조 규칙 데모", annotated)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
