"""통합 SOP 미니 데모 — 인원 수(N인 1조) + 사람별 보호구 착용 규칙.

두 모델을 한 루프에서 돌려 결과를 결합한다.
  - person 검출+추적: yolov8n.pt (COCO person) + ByteTrack -> 사람마다 고유 ID
  - 보호구 검출: models/helmet_v2_best.pt -> helmet / no_helmet 박스

"헬멧 박스가 보이면 착용"이 아니라, 각 person 박스 안에 helmet/no_helmet 박스의
중심점이 들어오는지로 "그 사람이 실제로 썼는가"를 판정한다 (webcam_test.md 한계 1 해결).
아무 보호구 박스도 못 찾으면 "미확인"으로 두고 위반 처리하지 않는다 (판정 보류 원칙).

규칙 2개, 둘 다 SustainedLatch(지속 시간 채워야 확정/해제)로 처리한다.
  - N인 1조: 인원 수 != N 이 지속 -> 위반 / N명 복귀 지속 -> 해제 (기획안 5.6절, 기본 N=2/3초)
  - 보호구 미착용: 특정 사람이 미착용 상태로 지속 -> 위반 / 착용 복귀 지속 -> 해제 (기본 10초)

작업마다 필요 인원 수가 다를 수 있어(2인 1조/3인 1조/4인 1조 등) 코드 수정 없이
커맨드라인 인자로 바꾼다. 다른 세정기 라인이나 작업에 바로 적용하려면:

    python webcam_sop.py --crew 3
    python webcam_sop.py --crew 4 --crew-hold 5 --helmet-hold 15

세부 파라미터는 --help 참고. 나중에 SOP를 JSON으로 구조화하면(Phase 3~4) 이 값들은
명령행 인자 대신 SOP 문서에서 읽어오도록 바뀔 예정 — 지금은 그 전 단계 임시 인터페이스.
"""

import argparse
import time
from collections import Counter, deque

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

PERSON_MODEL_PATH = "yolov8n.pt"
HELMET_MODEL_PATH = "models/helmet_v2_best.pt"
PERSON_CLASS = 0             # COCO 기준 person
PERSON_CONF = 0.4
HELMET_CONF = 0.5
IMGSZ = 480                  # 추론 입력 크기 (작을수록 빠름 -> FPS 상승 -> 추적 안정)
TRACKER = "trackers/bytetrack_person.yaml"

SMOOTH_SEC = 0.5             # 인원 수 / 개인별 상태 안정화 창

# 아래 4개는 --help 로 볼 수 있는 커맨드라인 인자의 기본값. 작업별로 다르면
# 코드를 고치지 말고 실행 시 --crew, --crew-hold 등으로 넘긴다.
DEFAULT_CREW = 2                  # N인 1조
DEFAULT_CREW_HOLD_SEC = 3.0       # 인원 수 위반 확정 지속 시간 (기획안 5.6절)
DEFAULT_CREW_CLEAR_SEC = 3.0

DEFAULT_HELMET_HOLD_SEC = 10.0    # 미착용 위반 확정 지속 시간 (3초는 빠듯해서 10초로 완화)
DEFAULT_HELMET_CLEAR_SEC = 10.0


def parse_args():
    p = argparse.ArgumentParser(description="SOP 통합 데모 (N인 1조 + 보호구 착용)")
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
    return p.parse_args()

try:
    _FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 20)
    _FONT_SMALL = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 16)
    _FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 30)
except OSError:
    _FONT = _FONT_SMALL = _FONT_BIG = ImageFont.load_default()

HELMET_LABELS = {0: "helmet", 1: "no_helmet"}
STATUS_COLOR = {
    "착용": (0, 170, 0),
    "미착용": (220, 30, 30),
    "미확인": (140, 140, 140),
}


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


def box_xyxy(b):
    x1, y1, x2, y2 = b.xyxy[0].tolist()
    return x1, y1, x2, y2


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


def draw_overlay(bgr, person_boxes, statuses, crew_banner, crew_rgb, helmet_violation_ids):
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img)

    for pid, box in person_boxes:
        x1, y1, x2, y2 = [int(v) for v in box]
        stable = statuses.get(pid, "미확인")
        color = STATUS_COLOR[stable]
        width = 3 if pid in helmet_violation_ids else 2
        d.rectangle([x1, y1, x2, y2], outline=color, width=width)
        tag = f"ID{pid} {stable}"
        if pid in helmet_violation_ids:
            tag += " (위반)"
        d.rectangle([x1, max(0, y1 - 22), x1 + 9 * len(tag), y1], fill=color)
        d.text((x1 + 2, max(0, y1 - 21)), tag, font=_FONT_SMALL, fill=(255, 255, 255))

    w, h = img.size
    d.rectangle([0, h - 56, w, h], fill=crew_rgb)
    d.text((16, h - 48), crew_banner, font=_FONT_BIG, fill=(255, 255, 255))

    if helmet_violation_ids:
        text = "보호구 미착용 위반: " + ", ".join(f"ID{i}" for i in sorted(helmet_violation_ids))
        tw = d.textlength(text, font=_FONT)
        d.rectangle([0, h - 82, tw + 24, h - 56], fill=(200, 60, 0))
        d.text((12, h - 78), text, font=_FONT, fill=(255, 255, 255))

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def main():
    args = parse_args()
    print(f"설정: {args.crew}인 1조 (확정 {args.crew_hold}초/해제 {args.crew_clear}초), "
          f"보호구 미착용 (확정 {args.helmet_hold}초/해제 {args.helmet_clear}초)")

    person_model = YOLO(PERSON_MODEL_PATH)
    helmet_model = YOLO(HELMET_MODEL_PATH)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return
    _run(cap, person_model, helmet_model, args)


def _run(cap, person_model, helmet_model, args):
    count_history = deque()          # (t, raw_count) — 인원 수 안정화
    crew_rule = SustainedLatch(args.crew_hold, args.crew_clear)
    person_states = {}               # track_id -> PersonState
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
        person_boxes_all = person_res[0].boxes
        person_items = [
            (int(b.id), box_xyxy(b)) for b in person_boxes_all if b.id is not None
        ]

        helmet_res = helmet_model(frame, conf=HELMET_CONF, verbose=False)
        helmet_boxes = helmet_res[0].boxes

        frame_status = match_helmet_to_persons(person_items, helmet_boxes)

        # 인원 수 안정화 (2인 1조 규칙)
        raw_count = len(person_items)
        count_history.append((now, raw_count))
        while count_history and now - count_history[0][0] > SMOOTH_SEC:
            count_history.popleft()
        stable_count = Counter(c for _, c in count_history).most_common(1)[0][0]
        crew_violation = crew_rule.update(stable_count != args.crew, now)

        # 사람별 보호구 상태 갱신 + 위반 판정
        statuses, helmet_violation_ids = {}, set()
        for pid, _ in person_items:
            state = person_states.setdefault(
                pid, PersonState(args.helmet_hold, args.helmet_clear)
            )
            stable, violated = state.update(frame_status.get(pid), now)
            statuses[pid] = stable
            if violated:
                helmet_violation_ids.add(pid)
        # 오래 안 보인 트랙 정리 (메모리 누수 방지)
        for pid in [p for p, s in person_states.items() if now - s.last_seen > 30]:
            del person_states[pid]

        if crew_violation:
            elapsed = int(now - crew_rule.latched_at)
            crew_banner, crew_rgb = f"{args.crew}인 1조 위반 ({elapsed}초)", (200, 0, 0)
        elif stable_count == args.crew:
            crew_banner, crew_rgb = f"정상 ({args.crew}인 1조)", (0, 140, 0)
        else:
            crew_banner, crew_rgb = f"감시 중 (인원 {stable_count})", (200, 130, 0)

        annotated = draw_overlay(frame, person_items, statuses, crew_banner, crew_rgb, helmet_violation_ids)

        fps = 1.0 / (now - prev_t) if now > prev_t else 0.0
        prev_t = now
        img = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        ImageDraw.Draw(img).text((12, 8), f"인원 {stable_count} (raw {raw_count})   {fps:.0f} FPS",
                                  font=_FONT, fill=(0, 255, 0))
        annotated = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        cv2.imshow("SOP 통합 데모 (2인1조 + 보호구 착용)", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
