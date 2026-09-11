"""안전구역 침범 검출 PoC — ArUco 마커로 "화면 좌표가 아니라 실세계 위치" 기준 구역 판정.

바디캠은 착용자가 움직이므로 화면에 고정 폴리곤을 그려두는 방식은 카메라가
돌아가는 순간 틀린 판정을 한다. 대신 위험구역 네 모서리에 ArUco 마커를 두고,
매 프레임 마커 위치로 구역 폴리곤을 다시 계산한다 — 카메라가 움직여도 마커만
보이면 구역이 따라오고, 마커가 안 보이면 "판정 보류"로 처리한다 (오판정 대신 침묵).

준비: generate_markers.py 로 만든 4장(ID 0~3, TL/TR/BR/BL)을 프린트해서
테스트할 구역의 네 모서리에 시계 방향으로 놓는다.

한계 (개념 검증 수준, 실전 적용 전 별도 작업 필요):
  - 마커 4개가 전부 보여야 구역을 인식한다 (부분 가림 대응은 다음 단계)
  - 종이 마커는 실내 테스트용. 현장은 방수·내구성 있는 재질로 별도 제작 필요
  - 지속시간(HOLD/CLEAR)은 임시값. 현장 실측 후 조정
"""

import time
from collections import Counter, deque

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

PERSON_MODEL_PATH = "yolov8n.pt"
PERSON_CLASS = 0
PERSON_CONF = 0.4
IMGSZ = 480
TRACKER = "trackers/bytetrack_person.yaml"

ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ZONE_MARKER_ORDER = [0, 1, 2, 3]   # TL, TR, BR, BL 순서 (generate_markers.py와 동일)

SMOOTH_SEC = 0.5
ZONE_HOLD_SEC = 3.0    # 구역 침범 확정 지속 시간 (임시값 — 위험요인, 2인1조와 동일하게 시작)
ZONE_CLEAR_SEC = 3.0

try:
    _FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 20)
    _FONT_SMALL = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 16)
    _FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 30)
except OSError:
    _FONT = _FONT_SMALL = _FONT_BIG = ImageFont.load_default()


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


class ZoneState:
    """트랙 ID 한 명의 "구역 안/밖" 이력 + 위반 판정.
    마커가 안 보여 판정 불가한 프레임(None)은 이력에서 제외하고, latch도 갱신하지 않는다
    (판정 보류 — 안전하지도 위반도 아닌 것으로 "모른다"를 명시)."""

    def __init__(self):
        self.history = deque()   # (t, True(안) | False(밖) | None(모름))
        self.latch = SustainedLatch(ZONE_HOLD_SEC, ZONE_CLEAR_SEC)
        self.last_seen = 0.0

    def update(self, inside, now):
        self.last_seen = now
        self.history.append((now, inside))
        while self.history and now - self.history[0][0] > SMOOTH_SEC:
            self.history.popleft()
        votes = [v for _, v in self.history if v is not None]
        if not votes:
            return None, self.latch.latched   # 최근 창에 정보 없음 -> 모름, latch 동결
        stable = Counter(votes).most_common(1)[0][0]
        violation = self.latch.update(stable, now)
        return stable, violation


def person_box_xyxy(b):
    x1, y1, x2, y2 = b.xyxy[0].tolist()
    return x1, y1, x2, y2


def foot_point(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, y2


def detect_zone_polygon(detector, frame):
    """마커 4개가 모두 보이면 (구역 폴리곤, 검출된 마커 id 목록) 반환, 아니면 (None, 검출목록)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    centers = {}
    if ids is not None:
        for c, i in zip(corners, ids.flatten()):
            centers[int(i)] = tuple(c[0].mean(axis=0))
    if all(mid in centers for mid in ZONE_MARKER_ORDER):
        poly = [centers[mid] for mid in ZONE_MARKER_ORDER]
        return poly, sorted(centers.keys())
    return None, sorted(centers.keys())


def draw_overlay(bgr, zone_poly, person_items, statuses, violation_ids, marker_ids_seen):
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)

    if zone_poly:
        d.polygon(zone_poly, outline=(255, 200, 0), width=3)
        d.text((zone_poly[0][0], zone_poly[0][1] - 24), "위험구역", font=_FONT_SMALL, fill=(255, 200, 0))

    for pid, box in person_items:
        x1, y1, x2, y2 = [int(v) for v in box]
        stable = statuses.get(pid, "미확인")
        color = {"안": (220, 30, 30), "밖": (0, 170, 0), "미확인": (140, 140, 140)}[stable]
        width = 3 if pid in violation_ids else 2
        d.rectangle([x1, y1, x2, y2], outline=color, width=width)
        tag = f"ID{pid} 구역{stable}" + (" (위반)" if pid in violation_ids else "")
        d.rectangle([x1, max(0, y1 - 22), x1 + 10 * len(tag), y1], fill=color)
        d.text((x1 + 2, max(0, y1 - 21)), tag, font=_FONT_SMALL, fill=(255, 255, 255))

    zone_status = f"마커 인식: {marker_ids_seen} / 필요 {ZONE_MARKER_ORDER}"
    d.text((12, 8), zone_status, font=_FONT, fill=(0, 255, 0) if zone_poly else (255, 120, 0))

    w, h = img.size
    if not zone_poly:
        banner, rgb = "구역 확인 불가 (마커 미검출)", (120, 120, 120)
    elif violation_ids:
        banner = "안전구역 침범: " + ", ".join(f"ID{i}" for i in sorted(violation_ids))
        rgb = (200, 0, 0)
    else:
        banner, rgb = "정상 (구역 밖)", (0, 140, 0)
    d.rectangle([0, h - 50, w, h], fill=rgb)
    d.text((16, h - 42), banner, font=_FONT_BIG, fill=(255, 255, 255))

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def main():
    person_model = YOLO(PERSON_MODEL_PATH)
    detector = cv2.aruco.ArucoDetector(ARUCO_DICT, cv2.aruco.DetectorParameters())

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    zone_states = {}   # track_id -> ZoneState
    prev_t = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("카메라 프레임을 읽을 수 없습니다.")
            break

        now = time.time()

        person_res = person_model.track(
            frame, classes=[PERSON_CLASS], conf=PERSON_CONF, imgsz=IMGSZ,
            persist=True, tracker=TRACKER, verbose=False,
        )
        person_items = [
            (int(b.id), person_box_xyxy(b)) for b in person_res[0].boxes if b.id is not None
        ]

        zone_poly, marker_ids_seen = detect_zone_polygon(detector, frame)
        zone_poly_i = [(int(x), int(y)) for x, y in zone_poly] if zone_poly else None

        statuses, violation_ids = {}, set()
        for pid, box in person_items:
            state = zone_states.setdefault(pid, ZoneState())
            if zone_poly:
                fp = foot_point(box)
                inside = cv2.pointPolygonTest(
                    np.array(zone_poly, dtype=np.float32), fp, False
                ) >= 0
            else:
                inside = None   # 구역 자체를 모르니 이 사람 상태도 모름
            stable, violated = state.update(inside, now)
            statuses[pid] = {True: "안", False: "밖", None: "미확인"}[stable]
            if violated:
                violation_ids.add(pid)
        for pid in [p for p, s in zone_states.items() if now - s.last_seen > 30]:
            del zone_states[pid]

        annotated = draw_overlay(frame, zone_poly_i, person_items, statuses, violation_ids, marker_ids_seen)

        fps = 1.0 / (now - prev_t) if now > prev_t else 0.0
        prev_t = now
        img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        ImageDraw.Draw(img).text((12, 34), f"{fps:.0f} FPS", font=_FONT_SMALL, fill=(0, 255, 0))
        annotated = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        cv2.imshow("안전구역 침범 PoC (ArUco)", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
