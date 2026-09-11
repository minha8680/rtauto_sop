"""안전구역 침범 검출 PoC — ArUco 마커로 "화면 좌표가 아니라 실세계 위치" 기준 구역 판정.

바디캠은 착용자가 움직이므로 화면에 고정 폴리곤을 그려두는 방식은 카메라가
돌아가는 순간 틀린 판정을 한다. 대신 위험구역 네 모서리에 ArUco 마커를 두고,
매 프레임 마커 위치로 구역 폴리곤을 다시 계산한다 — 카메라가 움직여도 마커만
보이면 구역이 따라오고, 마커가 안 보이면 "판정 보류"로 처리한다 (오판정 대신 침묵).

준비: generate_markers.py 로 만든 4장(ID 0~3, TL/TR/BR/BL)을 프린트해서
테스트할 구역의 네 모서리에 시계 방향으로 놓는다.

착용형 카메라(바디캠) 특유의 문제: 몸통 방향은 보통 지켜보는 대상을 향하지만,
호흡·발걸음 같은 미세한 흔들림만으로도 "이번 프레임에 마커 4개가 동시에" 조건이
깨지기 쉽다. 그래서 마커를 "이번 프레임에 보였는가"가 아니라 "최근 STALE_SEC
초 안에 한 번이라도 보였는가"로 판단한다 (MarkerMemory) — 짧은 순간 가려지거나
살짝 흔들려도 최근 위치를 그대로 써서 구역을 유지한다.

주의: 이 방식은 카메라가 그 짧은 시간 동안 "미세하게만" 움직였다는 전제다.
사람이 실제로 몸을 크게 홱 돌리면 직전 위치가 더 이상 맞지 않아 구역이 잘못
그려질 수 있다 — STALE_SEC를 너무 길게 잡지 않는 이유.

마커가 정확히 3개만 보이면(1개 가림) 평행사변형 근사로 4번째를 추정해 계속 판정한다
(사각형 대각선의 중점이 같다는 성질 이용). 화면에서 그 모서리는 빈 원(마젠타)으로
표시되어 "실측이 아니라 추정"임을 구분할 수 있다. 아래 ALLOW_ZONE_ESTIMATE = False 로 끌 수 있다
(webcam_sop.py에서는 같은 기능이 --no-zone-estimate 커맨드라인 인자다).

한계 (개념 검증 수준, 실전 적용 전 별도 작업 필요):
  - 3개 추정도 카메라가 정면에 가깝게 볼 때 잘 맞는 근사다. 각도가 심하게 기울면
    (원근 왜곡 큼) 오차가 커진다 — 완벽한 3D 복원이 아님
  - 마커가 2개 이하로 줄면 추정 자체가 불가능해 판정 보류로 돌아간다
  - 종이 마커는 실내 테스트용. 현장은 방수·내구성 있는 재질로 별도 제작 필요
  - 지속시간(HOLD/CLEAR, STALE_SEC)은 임시값. 현장 실측 후 조정
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

STALE_SEC = 0.4        # 마커를 "최근에 봤다"고 인정하는 시간 (카메라 미세 흔들림 흡수)
                        # 너무 길면 카메라가 실제로 크게 움직였을 때 옛 위치를 써서 오판정 위험 커짐
ALLOW_ZONE_ESTIMATE = True   # 마커 3개(1개 가림)일 때 평행사변형 근사로 4번째 추정. False면 예전처럼 4개 필수

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


class MarkerMemory:
    """각 마커 ID의 "마지막으로 본 위치와 시각"을 기억한다.
    이번 프레임에 안 보여도 STALE_SEC 안이면 그 위치를 그대로 쓴다 —
    카메라 미세 흔들림으로 인한 순간 미검출을 흡수하기 위함.

    마커가 정확히 3개만 있으면(1개 가림) 평행사변형 근사로 4번째를 추정한다:
    사각형 대각선의 중점이 같다는 성질(p0+p2 = p1+p3, TL+BR = TR+BL)을 이용해
    missing = adjacent1 + adjacent2 - opposite 로 계산한다. 카메라가 정면에
    가깝게 볼 때는 잘 맞고, 각도가 심하게 기울면(원근 왜곡 큼) 오차가 커진다 —
    완벽한 3D 복원이 아니라 "잠깐 하나 가려도 침묵하지 않기 위한" 근사다.
    allow_estimate=False 로 끄면 예전처럼 4개 다 있어야만 판정한다."""

    def __init__(self, stale_sec, allow_estimate=True):
        self.stale_sec = stale_sec
        self.allow_estimate = allow_estimate
        self.seen = {}   # id -> (point, t)

    def observe(self, current, now):
        """current: 이번 프레임에서 검출된 {id: point}."""
        for mid, pt in current.items():
            self.seen[mid] = (pt, now)

    def _fresh_points(self, now):
        """ZONE_MARKER_ORDER 안에서의 인덱스(0~3) -> 좌표, 최근 stale_sec 이내인 것만."""
        pts = {}
        for idx, mid in enumerate(ZONE_MARKER_ORDER):
            if mid in self.seen:
                pt, t = self.seen[mid]
                if now - t <= self.stale_sec:
                    pts[idx] = pt
        return pts

    def _status(self, idx, now):
        mid = ZONE_MARKER_ORDER[idx]
        age = now - self.seen[mid][1]
        return "live" if age < 1e-6 else "memory"

    def zone_polygon(self, now):
        """반환: (폴리곤[4점] 또는 None, 모서리별 상태 리스트["live"|"memory"|"estimated"] 또는 None)."""
        pts = self._fresh_points(now)

        if len(pts) == 4:
            poly = [pts[i] for i in range(4)]
            status = [self._status(i, now) for i in range(4)]
            return poly, status

        if len(pts) == 3 and self.allow_estimate:
            missing = next(i for i in range(4) if i not in pts)
            opposite = (missing + 2) % 4
            adj_a, adj_b = (missing + 1) % 4, (missing + 3) % 4
            est = (
                pts[adj_a][0] + pts[adj_b][0] - pts[opposite][0],
                pts[adj_a][1] + pts[adj_b][1] - pts[opposite][1],
            )
            poly, status = [], []
            for i in range(4):
                if i == missing:
                    poly.append(est)
                    status.append("estimated")
                else:
                    poly.append(pts[i])
                    status.append(self._status(i, now))
            return poly, status

        return None, None


def detect_zone_polygon(detector, frame, memory, now):
    """마커를 검출하고 memory에 기록한 뒤, memory 기준(최근 STALE_SEC 이내, 필요시 3점 추정)으로
    구역 폴리곤을 반환한다. 반환: (폴리곤 또는 None, 검출목록, 모서리별 상태 또는 None)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    current = {}
    if ids is not None:
        for c, i in zip(corners, ids.flatten()):
            current[int(i)] = tuple(c[0].mean(axis=0))
    memory.observe(current, now)
    poly, status = memory.zone_polygon(now)
    return poly, sorted(current.keys()), status


CORNER_DOT_COLOR = {
    "live": (0, 255, 0),        # 이번 프레임에 실제로 검출
    "memory": (255, 160, 0),    # 최근(STALE_SEC 이내) 기억한 위치 사용
    "estimated": (255, 0, 190), # 3개로 평행사변형 근사 추정
}


def draw_overlay(bgr, zone_poly, zone_status, person_items, statuses, violation_ids, marker_ids_seen):
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)

    if zone_poly:
        estimated = zone_status.count("estimated") if zone_status else 0
        zone_label = "위험구역" + (" (1개 추정)" if estimated else "")
        d.polygon(zone_poly, outline=(255, 200, 0), width=3)
        d.text((zone_poly[0][0], zone_poly[0][1] - 24), zone_label, font=_FONT_SMALL, fill=(255, 200, 0))
        # 모서리 점: 초록 = 실시간 검출, 주황 = 최근 기억, 빈 마젠타 원 = 3점으로 추정
        for (x, y), st in zip(zone_poly, zone_status):
            c = CORNER_DOT_COLOR[st]
            if st == "estimated":
                d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=c, width=2)
            else:
                d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=c)

    for pid, box in person_items:
        x1, y1, x2, y2 = [int(v) for v in box]
        stable = statuses.get(pid, "미확인")
        color = {"안": (220, 30, 30), "밖": (0, 170, 0), "미확인": (140, 140, 140)}[stable]
        width = 3 if pid in violation_ids else 2
        d.rectangle([x1, y1, x2, y2], outline=color, width=width)
        tag = f"ID{pid} 구역{stable}" + (" (위반)" if pid in violation_ids else "")
        d.rectangle([x1, max(0, y1 - 22), x1 + 10 * len(tag), y1], fill=color)
        d.text((x1 + 2, max(0, y1 - 21)), tag, font=_FONT_SMALL, fill=(255, 255, 255))

    marker_status_text = f"마커 인식: {marker_ids_seen} / 필요 {ZONE_MARKER_ORDER}"
    d.text((12, 8), marker_status_text, font=_FONT, fill=(0, 255, 0) if zone_poly else (255, 120, 0))

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
    marker_memory = MarkerMemory(STALE_SEC, allow_estimate=ALLOW_ZONE_ESTIMATE)
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

        zone_poly, marker_ids_seen, zone_corner_status = detect_zone_polygon(detector, frame, marker_memory, now)
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

        annotated = draw_overlay(frame, zone_poly_i, zone_corner_status, person_items, statuses, violation_ids, marker_ids_seen)

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
