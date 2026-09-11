"""events.jsonl(webcam_sop.py가 남긴 위반 확정/해제/클립저장 이력)을 사람이 읽기 쉽게 보여준다.

JSON Lines를 한 줄씩 직접 읽어도 되지만, confirmed/resolved를 짝지어서
"몇 초간 지속됐는지"까지 계산해서 보여주는 게 이 스크립트의 역할. clip_saved(경보 구간
클립 저장 완료, --no-clip 아니면 confirmed마다 하나씩 생김)는 파일 경로를 그대로 보여준다.

사용:
    python view_events.py              # 전체 이력
    python view_events.py --rule zone  # 특정 규칙만
    python view_events.py --today      # 오늘 것만
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime

EVENTS_LOG_PATH = "events.jsonl"

KIND_LABEL = {"confirmed": "확정", "resolved": "해제", "clip_saved": "클립"}


def load_events(path):
    if not os.path.exists(path):
        return []
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def main():
    p = argparse.ArgumentParser(description="이벤트 로그 뷰어")
    p.add_argument("--rule", default=None, help="이 규칙만 보기 (crew/helmet/zone 등)")
    p.add_argument("--today", action="store_true", help="오늘 발생한 것만 보기")
    p.add_argument("--log", default=EVENTS_LOG_PATH, help=f"로그 파일 경로 (기본 {EVENTS_LOG_PATH})")
    args = p.parse_args()

    events = load_events(args.log)
    if not events:
        print(f"{args.log} 가 없거나 비어있습니다. webcam_sop.py를 실행해 위반이 한 번이라도 "
              f"확정되면 기록이 남습니다.")
        return

    if args.rule:
        events = [e for e in events if e["rule"] == args.rule]
    if args.today:
        today = datetime.now().strftime("%Y-%m-%d")
        events = [e for e in events if e["ts"].startswith(today)]

    if not events:
        print("조건에 맞는 이벤트가 없습니다.")
        return

    print(f"총 {len(events)}건\n")

    # confirmed -> resolved 짝을 지어서 지속시간 계산 (규칙+대상 별로)
    open_since = {}
    for e in events:
        key = (e["rule"], e["target"])
        ts = datetime.fromisoformat(e["ts"])
        label = KIND_LABEL.get(e["kind"], e["kind"])
        target_str = f" (ID{e['target']})" if e["target"] is not None else ""

        line = f"{e['ts']}  [{label:2}] {e['rule']}{target_str}  {e['detail']}"

        if e["kind"] == "confirmed":
            open_since[key] = ts
        elif e["kind"] == "resolved" and key in open_since:
            duration = (ts - open_since.pop(key)).total_seconds()
            line += f"   -- 지속 {duration:.0f}초"

        print(line)

    if open_since:
        print(f"\n※ 아직 해제 안 된 위반 {len(open_since)}건: "
              + ", ".join(f"{r}{'(ID'+str(t)+')' if t is not None else ''}" for r, t in open_since))

    # 규칙별 요약
    counts = defaultdict(int)
    for e in events:
        if e["kind"] == "confirmed":
            counts[e["rule"]] += 1
    if counts:
        print("\n규칙별 확정 횟수:", dict(counts))


if __name__ == "__main__":
    main()
