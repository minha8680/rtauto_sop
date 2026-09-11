"""통합 SOP 미니 데모 — 인원 수(N인 1조) + 사람별 보호구 착용 + 안전구역 침범.

세 모델/검출기를 한 루프에서 돌려 결과를 결합한다.
  - person 검출+추적: yolov8n.pt (COCO person) + ByteTrack -> 사람마다 고유 ID
  - 보호구 검출: models/helmet_v2_best.pt -> helmet / no_helmet 박스
  - 안전구역: ArUco 마커 4개로 구역 폴리곤을 매 프레임 재계산 (webcam_zone.py 로직)

"헬멧 박스가 보이면 착용"이 아니라, 각 person 박스 안에 helmet/no_helmet 박스의
중심점이 들어오는지로 "그 사람이 실제로 썼는가"를 판정한다 (webcam_test.md 한계 1 해결).
안전구역도 마찬가지로 "화면 좌표 고정"이 아니라 마커 위치 기준으로 재계산한다 —
착용형 카메라가 움직여도 구역이 따라오고, 마커가 안 보이면 판정 보류로 침묵한다.
마커 4개 중 1개가 가려져 3개만 보이면, 평행사변형 근사(대각선 중점이 같다는 성질)로
4번째를 추정해 계속 판정한다 — 화면에 그 모서리는 빈 원(마젠타색)으로 표시되어
"이건 실측이 아니라 추정"임을 구분할 수 있다. --no-zone-estimate 로 끌 수 있다.
준비물(마커 인쇄·배치)은 webcam_zone.py 상단 docstring 참고.

규칙 3개, 전부 SustainedLatch(지속 시간 채워야 확정/해제)로 처리한다.
  - N인 1조: 인원 수 != N 이 지속 -> 위반 / N명 복귀 지속 -> 해제 (기획안 5.6절, 기본 N=2/3초)
  - 보호구 미착용: 특정 사람이 미착용 상태로 지속 -> 위반 / 착용 복귀 지속 -> 해제 (기본 10초)
  - 안전구역 침범: 특정 사람이 구역 안에 지속 -> 위반 / 구역 밖 복귀 지속 -> 해제 (기본 3초)

작업마다 필요 인원 수·지속시간이 다를 수 있어 코드 수정 없이 커맨드라인 인자로 바꾼다:

    python webcam_sop.py --crew 3
    python webcam_sop.py --crew 4 --crew-hold 5 --helmet-hold 15 --zone-hold 5

세부 파라미터는 --help 참고. 나중에 SOP를 JSON으로 구조화하면 이 값들은 명령행 인자 대신
SOP 문서에서 읽어오도록 바뀔 예정 — 지금은 그 전 단계 임시 인터페이스.

push_server.py(Web Push 프로토타입)를 같이 띄워두면 --push-url 로 실제 알림 연동:

    uvicorn push_server:app --port 8000        # 다른 터미널에서 먼저 실행
    python webcam_sop.py --push-url http://localhost:8000/notify

위반이 "새로 확정된 순간"에만 알림을 보낸다. 반복 억제·등급별 차등은 아직 없음(프로토타입).
"""

import argparse
import time
from collections import Counter, deque

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

PERSON_MODEL_PATH = "yolov8n.pt"
HELMET_MODEL_PATH = "models/helmet_v2_best.pt"
PERSON_CLASS = 0             # COCO 기준 person
PERSON_CONF = 0.4
HELMET_CONF = 0.5
IMGSZ = 480                  # 추론 입력 크기 (작을수록 빠름 -> FPS 상승 -> 추적 안정)
TRACKER = "trackers/bytetrack_person.yaml"

ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
ZONE_MARKER_ORDER = [0, 1, 2, 3]   # TL, TR, BR, BL 순서 (generate_markers.py와 동일)
STALE_SEC = 0.4                    # 마커를 "최근에 봤다"고 인정하는 시간 (카메라 미세 흔들림 흡수)

SMOOTH_SEC = 0.5             # 인원 수 / 개인별 상태 안정화 창

# 아래는 --help 로 볼 수 있는 커맨드라인 인자의 기본값. 작업별로 다르면
# 코드를 고치지 말고 실행 시 --crew, --crew-hold 등으로 넘긴다.
DEFAULT_CREW = 2                  # N인 1조
DEFAULT_CREW_HOLD_SEC = 3.0       # 인원 수 위반 확정 지속 시간 (기획안 5.6절)
DEFAULT_CREW_CLEAR_SEC = 3.0

DEFAULT_HELMET_HOLD_SEC = 10.0    # 미착용 위반 확정 지속 시간 (3초는 빠듯해서 10초로 완화)
DEFAULT_HELMET_CLEAR_SEC = 10.0

DEFAULT_ZONE_HOLD_SEC = 3.0       # 구역 침범 확정 지속 시간 (위험요인, 2인1조와 동일하게 시작)
DEFAULT_ZONE_CLEAR_SEC = 3.0


def parse_args():
    p = argparse.ArgumentParser(description="SOP 통합 데모 (N인 1조 + 보호구 착용 + 안전구역)")
    p.add_argument("--crew", type=int, default=DEFAULT_CREW,
                    help=f"필요 인원 수 (기본 {DEFAULT_CREW})")
    p.add_argument("--crew-hold", type=float, default=DEFAULT_CREW_HOLD_SEC,
                    help=f"인원 수 위반 확정까지 지속 시간(초) (기본 {DEFAULT_CREW_HOLD_SEC})")
    p.add_argument("--crew-clear", type=float, default=DEFAULT_CREW_CLEAR_SEC,
                    help=f"인원 수 위반 해제까지 지속 시간(초) (기본 {DEFAULT_CREW_CLEAR_SEC})")
    p.add_argument("--helmet-hold", type=float, default=DEFAULT_HELMET_HOLD_SEC,
                    help=f"보호구 미착용 위반 확정까지 지속 시간(초) (기본 {DEFAULT_HELMET_HOLD_SEC})")
    p.add_argument("--helmet-clear", type=float, default=DEFAULT_HELMET_CLEAR_SEC,
                    help=f"보호구 미착용 위반 해제까지 지속 시간(초) (기본 {DEFAULT_HELMET_CLEAR_SEC})")
    p.add_argument("--zone-hold", type=float, default=DEFAULT_ZONE_HOLD_SEC,
                    help=f"안전구역 침범 확정까지 지속 시간(초) (기본 {DEFAULT_ZONE_HOLD_SEC})")
    p.add_argument("--zone-clear", type=float, default=DEFAULT_ZONE_CLEAR_SEC,
                    help=f"안전구역 침범 해제까지 지속 시간(초) (기본 {DEFAULT_ZONE_CLEAR_SEC})")
    p.add_argument("--no-zone", action="store_true",
                    help="마커를 준비 못 했을 때 안전구역 판정을 끄고 인원수+보호구만 실행")
    p.add_argument("--no-zone-estimate", action="store_true",
                    help="마커 3개(1개 가림)일 때 평행사변형 근사로 4번째를 추정하는 기능을 끄고, "
                         "예전처럼 4개 다 보여야만 구역을 판정. 추정이 못 미더울 때 검증용")
    p.add_argument("--push-url", type=str, default=None,
                    help="위반 '확정' 순간(재발 아님, 새로 걸릴 때만) push_server.py의 /notify로 "
                         "POST 요청. 예: http://localhost:8000/notify. 생략하면 알림 전송 안 함")
    return p.parse_args()


def send_push(push_url, title, body):
    """push_server.py /notify 로 알림 발송. 실패해도 메인 루프는 계속 돈다(프로토타입이므로)."""
    if not push_url:
        return
    try:
        requests.post(push_url, json={"title": title, "body": body}, timeout=1.5)
    except Exception as e:
        print(f"[push] 알림 발송 실패: {e}")


try:
    _FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 20)
    _FONT_SMALL = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 16)
    _FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 30)
except OSError:
    _FONT = _FONT_SMALL = _FONT_BIG = ImageFont.load_default()

HELMET_LABELS = {0: "helmet", 1: "no_helmet"}


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


class PersonState:
    """트랙 ID 하나(사람 한 명)의 보호구 착용 상태 이력 + 위반 판정."""

    def __init__(self, hold_sec=DEFAULT_HELMET_HOLD_SEC, clear_sec=DEFAULT_HELMET_CLEAR_SEC):
        self.history = deque()   # (t, "착용" | "미착용" | None)
        self.latch = SustainedLatch(hold_sec, clear_sec)
        self.last_seen = 0.0

    def update(self, status, now):
        self.last_seen = now
        self.history.append((now, status))
        while self.history and now - self.history[0][0] > SMOOTH_SEC:
            self.history.popleft()
        votes = [s for _, s in self.history if s is not None]
        stable = Counter(votes).most_common(1)[0][0] if votes else "미확인"
        violation = self.latch.update(stable == "미착용", now)
        return stable, violation


class ZoneState:
    """트랙 ID 하나(사람 한 명)의 "구역 안/밖" 이력 + 위반 판정.
    마커가 안 보여 판정 불가한 프레임(None)은 이력에서 제외하고, latch도 갱신하지 않는다
    (판정 보류 — 안전하지도 위반도 아닌 것으로 "모른다"를 명시)."""

    def __init__(self, hold_sec=DEFAULT_ZONE_HOLD_SEC, clear_sec=DEFAULT_ZONE_CLEAR_SEC):
        self.history = deque()   # (t, True(안) | False(밖) | None(모름))
        self.latch = SustainedLatch(hold_sec, clear_sec)
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


def box_xyxy(b):
    x1, y1, x2, y2 = b.xyxy[0].tolist()
    return x1, y1, x2, y2


def foot_point(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, y2


def match_helmet_to_persons(person_items, helmet_boxes):
    """helmet/no_helmet 박스 중심이 들어있는 person 박스에 배정.
    여러 person과 겹치면 가장 작은(가까운) person 박스 우선, 중복 매칭 시 confidence 높은 쪽."""
    assigned = {pid: None for pid, _ in person_items}   # pid -> (label, conf)
    for hb in helmet_boxes:
        hx1, hy1, hx2, hy2 = box_xyxy(hb)
        cx, cy = (hx1 + hx2) / 2, (hy1 + hy2) / 2
        label = HELMET_LABELS.get(int(hb.cls[0]), "?")
        conf = float(hb.conf[0])

        best_pid, best_area = None, None
        for pid, pbox in person_items:
            px1, py1, px2, py2 = pbox
            if px1 <= cx <= px2 and py1 <= cy <= py2:
                area = (px2 - px1) * (py2 - py1)
                if best_area is None or area < best_area:
                    best_pid, best_area = pid, area
        if best_pid is None:
            continue
        prev = assigned[best_pid]
        if prev is None or conf > prev[1]:
            assigned[best_pid] = (label, conf)

    out = {}
    for pid, val in assigned.items():
        out[pid] = "착용" if (val and val[0] == "helmet") else ("미착용" if val else None)
    return out


def detect_zone_polygon(detector, frame, memory, now):
    """반환: (폴리곤 또는 None, 검출된 마커 id 목록, 모서리별 상태["live"|"memory"|"estimated"])."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    current = {}
    if ids is not None:
        for c, i in zip(corners, ids.flatten()):
            current[int(i)] = tuple(c[0].mean(axis=0))
    memory.observe(current, now)
    poly, status = memory.zone_polygon(now)
    return poly, sorted(current.keys()), status


def combined_color(helmet_stat, zone_stat, is_violation):
    """사람 박스/라벨 색: 위반 확정=빨강, 위반 소지(미착용 또는 구역안)=주황,
    둘 다 정상 확인됨=초록, 둘 다 모름=회색."""
    if is_violation:
        return (220, 30, 30)
    if helmet_stat == "미착용" or zone_stat == "안":
        return (230, 150, 0)
    if helmet_stat == "미확인" and zone_stat == "미확인":
        return (140, 140, 140)
    return (0, 170, 0)


CORNER_DOT_COLOR = {
    "live": (0, 255, 0),        # 이번 프레임에 실제로 검출
    "memory": (255, 160, 0),    # 최근(STALE_SEC 이내) 기억한 위치 사용
    "estimated": (255, 0, 190), # 3개로 평행사변형 근사 추정
}


def draw_overlay(bgr, zone_poly, zone_status, marker_ids_seen, person_items,
                  helmet_status, zone_person_status, helmet_violation_ids, zone_violation_ids,
                  crew_banner, crew_rgb, zone_enabled):
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)

    if zone_poly:
        estimated = zone_status.count("estimated") if zone_status else 0
        zone_label = "위험구역" + (" (1개 추정)" if estimated else "")
        d.polygon(zone_poly, outline=(255, 200, 0), width=3)
        d.text((zone_poly[0][0], zone_poly[0][1] - 24), zone_label, font=_FONT_SMALL, fill=(255, 200, 0))
        for (x, y), st in zip(zone_poly, zone_status):
            c = CORNER_DOT_COLOR[st]
            if st == "estimated":
                d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=c, width=2)   # 빈 원 = "실측 아님" 표시
            else:
                d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=c)

    for pid, box in person_items:
        x1, y1, x2, y2 = [int(v) for v in box]
        h_stat = helmet_status.get(pid, "미확인")
        z_stat = zone_person_status.get(pid, "미확인") if zone_enabled else "미확인"
        violated = pid in helmet_violation_ids or pid in zone_violation_ids
        color = combined_color(h_stat, z_stat, violated)

        tags = []
        if pid in helmet_violation_ids:
            tags.append("헬멧위반")
        if pid in zone_violation_ids:
            tags.append("구역위반")
        suffix = " " + "/".join(tags) if tags else ""
        if zone_enabled:
            tag = f"ID{pid} 헬멧:{h_stat} 구역:{z_stat}{suffix}"
        else:
            tag = f"ID{pid} 헬멧:{h_stat}{suffix}"

        width = 3 if violated else 2
        d.rectangle([x1, y1, x2, y2], outline=color, width=width)
        d.rectangle([x1, max(0, y1 - 22), x1 + 9 * len(tag), y1], fill=color)
        d.text((x1 + 2, max(0, y1 - 21)), tag, font=_FONT_SMALL, fill=(255, 255, 255))

    top2 = f"마커 인식: {marker_ids_seen} / 필요 {ZONE_MARKER_ORDER}" if zone_enabled else "안전구역 판정 꺼짐 (--no-zone)"
    d.text((12, 34), top2, font=_FONT_SMALL, fill=(0, 255, 0) if zone_poly else (255, 120, 0))

    w, h = img.size
    bands = [(crew_banner, crew_rgb, _FONT_BIG, 56)]
    if helmet_violation_ids:
        text = "보호구 미착용 위반: " + ", ".join(f"ID{i}" for i in sorted(helmet_violation_ids))
        bands.append((text, (200, 60, 0), _FONT, 26))
    if zone_enabled and zone_violation_ids:
        text = "안전구역 침범: " + ", ".join(f"ID{i}" for i in sorted(zone_violation_ids))
        bands.append((text, (200, 0, 0), _FONT, 26))

    y_cursor = h
    for text, rgb, font, height in bands:
        y0 = y_cursor - height
        d.rectangle([0, y0, w, y_cursor], fill=rgb)
        pad = 8 if height >= 40 else 4
        d.text((16, y0 + pad), text, font=font, fill=(255, 255, 255))
        y_cursor = y0

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def main():
    args = parse_args()
    zone_enabled = not args.no_zone
    print(f"설정: {args.crew}인 1조 (확정 {args.crew_hold}초/해제 {args.crew_clear}초), "
          f"보호구 미착용 (확정 {args.helmet_hold}초/해제 {args.helmet_clear}초), "
          + (f"안전구역 침범 (확정 {args.zone_hold}초/해제 {args.zone_clear}초)"
             if zone_enabled else "안전구역 판정 꺼짐"))

    person_model = YOLO(PERSON_MODEL_PATH)
    helmet_model = YOLO(HELMET_MODEL_PATH)
    detector = cv2.aruco.ArucoDetector(ARUCO_DICT, cv2.aruco.DetectorParameters())

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return
    _run(cap, person_model, helmet_model, detector, args, zone_enabled)


def _run(cap, person_model, helmet_model, detector, args, zone_enabled):
    count_history = deque()          # (t, raw_count) — 인원 수 안정화
    crew_rule = SustainedLatch(args.crew_hold, args.crew_clear)
    person_states = {}               # track_id -> PersonState (보호구)
    zone_states = {}                 # track_id -> ZoneState (안전구역)
    marker_memory = MarkerMemory(STALE_SEC, allow_estimate=not args.no_zone_estimate)
    prev_t = time.time()

    # 알림은 "새로 위반이 걸린 순간"에만 보낸다 (반복 억제는 여기선 안 함 — 프로토타입)
    prev_crew_violation = False
    prev_helmet_violation_ids = set()
    prev_zone_violation_ids = set()

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
            (int(b.id), box_xyxy(b)) for b in person_res[0].boxes if b.id is not None
        ]

        helmet_res = helmet_model(frame, conf=HELMET_CONF, verbose=False)
        frame_helmet_status = match_helmet_to_persons(person_items, helmet_res[0].boxes)

        if zone_enabled:
            zone_poly, marker_ids_seen, zone_corner_status = detect_zone_polygon(detector, frame, marker_memory, now)
        else:
            zone_poly, marker_ids_seen, zone_corner_status = None, [], None
        zone_poly_i = [(int(x), int(y)) for x, y in zone_poly] if zone_poly else None

        # 인원 수 안정화 (N인 1조 규칙)
        raw_count = len(person_items)
        count_history.append((now, raw_count))
        while count_history and now - count_history[0][0] > SMOOTH_SEC:
            count_history.popleft()
        stable_count = Counter(c for _, c in count_history).most_common(1)[0][0]
        crew_violation = crew_rule.update(stable_count != args.crew, now)

        # 사람별 보호구 + 안전구역 상태 갱신
        helmet_status, zone_status = {}, {}
        helmet_violation_ids, zone_violation_ids = set(), set()
        for pid, box in person_items:
            pstate = person_states.setdefault(pid, PersonState(args.helmet_hold, args.helmet_clear))
            h_stable, h_violated = pstate.update(frame_helmet_status.get(pid), now)
            helmet_status[pid] = h_stable
            if h_violated:
                helmet_violation_ids.add(pid)

            if zone_enabled:
                zstate = zone_states.setdefault(pid, ZoneState(args.zone_hold, args.zone_clear))
                if zone_poly:
                    inside = cv2.pointPolygonTest(
                        np.array(zone_poly, dtype=np.float32), foot_point(box), False
                    ) >= 0
                else:
                    inside = None
                z_stable, z_violated = zstate.update(inside, now)
                zone_status[pid] = {True: "안", False: "밖", None: "미확인"}[z_stable]
                if z_violated:
                    zone_violation_ids.add(pid)

        for pid in [p for p, s in person_states.items() if now - s.last_seen > 30]:
            del person_states[pid]
        for pid in [p for p, s in zone_states.items() if now - s.last_seen > 30]:
            del zone_states[pid]

        if crew_violation:
            elapsed = int(now - crew_rule.latched_at)
            crew_banner, crew_rgb = f"{args.crew}인 1조 위반 ({elapsed}초)", (200, 0, 0)
        elif stable_count == args.crew:
            crew_banner, crew_rgb = f"정상 ({args.crew}인 1조)", (0, 140, 0)
        else:
            crew_banner, crew_rgb = f"감시 중 (인원 {stable_count})", (200, 130, 0)

        if args.push_url:
            if crew_violation and not prev_crew_violation:
                send_push(args.push_url, "중대 편차 발생", f"{args.crew}인 1조 위반")
            for pid in helmet_violation_ids - prev_helmet_violation_ids:
                send_push(args.push_url, "보호구 미착용", f"작업자 ID{pid} 미착용 지속")
            for pid in zone_violation_ids - prev_zone_violation_ids:
                send_push(args.push_url, "안전구역 침범", f"작업자 ID{pid} 구역 내 위치")
            prev_crew_violation = crew_violation
            prev_helmet_violation_ids = set(helmet_violation_ids)
            prev_zone_violation_ids = set(zone_violation_ids)

        annotated = draw_overlay(
            frame, zone_poly_i, zone_corner_status, marker_ids_seen, person_items,
            helmet_status, zone_status, helmet_violation_ids, zone_violation_ids,
            crew_banner, crew_rgb, zone_enabled,
        )

        fps = 1.0 / (now - prev_t) if now > prev_t else 0.0
        prev_t = now
        img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        ImageDraw.Draw(img).text((12, 8), f"인원 {stable_count} (raw {raw_count})   {fps:.0f} FPS",
                                  font=_FONT, fill=(0, 255, 0))
        annotated = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        cv2.imshow("SOP 통합 데모 (N인1조 + 보호구 + 안전구역)", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
