# -*- coding: utf-8 -*-
"""RTSP 연결 자체만 검증하는 최소 스크립트 -- 포팩트 LIVE ST20 입고 직후 가장 먼저 돌려볼 것.

검출 모델은 전혀 쓰지 않는다(webcam_helmet.py 등과 다름). 순수하게 "SoftAP를 거쳐 RTSP
스트림이 끊김 없이 들어오는가"만 확인한다 -- 기획안 5.1절 구간 ①의 지연 목표(0.5초 이내)와
CLAUDE.md가 지적한 "버퍼링·지연 관리, 끊김 재연결"이 실제로 얼마나 문제인지 여기서 먼저 잰다.
이 스크립트가 통과해야 그 다음(webcam_sop.py를 RTSP로 붙이는 작업, 검출 품질 검증)이 의미가
있다 -- 연결 자체가 불안정하면 검출 결과를 믿을 수 없기 때문.

사용법:
    python rtsp_test.py rtsp://<카메라IP>:<포트>/<경로>

RTSP 주소는 카메라 앱/매뉴얼에서 확인. 모르면 흔한 형식을 순서대로 시도해볼 것(제조사마다
다름):
    rtsp://<IP>/live
    rtsp://<IP>:554/stream1
    rtsp://<IP>/h264
아이디/비번이 필요하면 rtsp://user:pass@<IP>/... 형식으로 넣는다.

화면 없이 콘솔 로그만 보려면 --no-display (장시간 배터리 지속시간 테스트와 같이 돌릴 때 유용).

연결을 여는 로직 자체(CAP_FFMPEG, 저지연 버퍼, 타임아웃)는 video_source.py에 공통 함수로
분리해서 webcam_sop.py --source rtsp://... 와 공유한다 -- 여기서 검증한 설정 그대로
webcam_sop.py에서도 쓰인다는 뜻. 이 파일엔 그 위에 얹은 "재연결·지연 진단" 로직만 남는다.
"""
import argparse
import time
from collections import deque

import cv2

from video_source import open_video_source

RECONNECT_MAX = 5          # 연속 재연결 시도 횟수
RECONNECT_WAIT_SEC = 2.0   # 재연결 사이 대기
FPS_WINDOW = 30             # 최근 N프레임으로 실측 FPS 계산
STALL_TIMEOUT_SEC = 3.0     # 이 시간 동안 새 프레임을 못 받으면 끊김으로 판정
REPORT_EVERY_SEC = 5.0      # 콘솔 상태 출력 주기

# CAP_PROP_OPEN/READ_TIMEOUT_MSEC은 video_source.py에서 이미 적용됨. FFmpeg 빌드에 따라
# 정확히 지켜지지 않을 수 있음을 로컬 테스트로 확인함(주소가 완전히 잘못됐을 때 설정값보다
# 오래 멈추는 경우 있었음) -- 그래도 안 거는 것보단 낫다. 정말 안 풀리면 Ctrl+C를 여러 번
# 누르거나 터미널 자체를 닫을 것.


def reconnect(url):
    """RECONNECT_MAX 번까지 재시도. 성공하면 새 cap, 실패하면 None."""
    for attempt in range(1, RECONNECT_MAX + 1):
        time.sleep(RECONNECT_WAIT_SEC)
        print(f"[rtsp_test] 재연결 시도 {attempt}/{RECONNECT_MAX}", flush=True)
        cap = open_video_source(url)
        if cap.isOpened():
            print(f"[rtsp_test] 재연결 성공 (시도 {attempt}번째)", flush=True)
            return cap
        cap.release()
    return None


def main():
    ap = argparse.ArgumentParser(description="RTSP 연결/지연/재연결만 검증 (검출 모델 없음)")
    ap.add_argument("url", help="rtsp://... 스트림 주소")
    ap.add_argument("--no-display", action="store_true", help="화면 표시 없이 콘솔 로그만 출력")
    args = ap.parse_args()

    print(f"[rtsp_test] 연결 시도: {args.url}", flush=True)
    cap = open_video_source(args.url)
    if not cap.isOpened():
        print("[rtsp_test] 연결 실패 - 주소/포트, SoftAP 접속 상태, 카메라 전원을 확인하세요.", flush=True)
        return

    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps_reported = cap.get(cv2.CAP_PROP_FPS)
    print(f"[rtsp_test] 연결 성공 - 수신 해상도 {w:.0f}x{h:.0f}, 스트림 공표 FPS {fps_reported:.1f}", flush=True)
    print("[rtsp_test] 기획안 목표: 1080p 15fps, 지연 0.5초 이내. q 로 종료, "
          f"{REPORT_EVERY_SEC:.0f}초마다 실측 FPS/재연결/끊김 횟수를 출력합니다.", flush=True)

    frame_times = deque(maxlen=FPS_WINDOW)
    last_frame_at = time.time()
    reconnects = 0
    stalls = 0
    dead = False
    last_report = time.time()
    start = time.time()

    try:
        while True:
            ok, frame = cap.read()
            now = time.time()

            if not ok:
                gap = now - last_frame_at
                if gap >= STALL_TIMEOUT_SEC:
                    stalls += 1
                    print(f"[rtsp_test] 끊김 감지({gap:.1f}초 무응답)", flush=True)
                    cap.release()
                    new_cap = reconnect(args.url)
                    if new_cap is None:
                        print("[rtsp_test] 재연결 실패 - 종료", flush=True)
                        dead = True
                        break
                    cap = new_cap
                    reconnects += 1
                    last_frame_at = time.time()
                continue

            last_frame_at = now
            frame_times.append(now)

            if not args.no_display:
                cv2.imshow("RTSP 연결 테스트 (검출 없음)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            if now - last_report >= REPORT_EVERY_SEC:
                if len(frame_times) >= 2:
                    measured_fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0])
                else:
                    measured_fps = 0.0
                elapsed = now - start
                print(f"[rtsp_test] {elapsed:6.0f}s 경과 | 실측 FPS {measured_fps:4.1f} "
                      f"| 재연결 {reconnects}회 | 끊김 {stalls}회", flush=True)
                last_report = now
    except KeyboardInterrupt:
        print("\n[rtsp_test] 사용자 중단(Ctrl+C)", flush=True)

    cap.release()
    cv2.destroyAllWindows()
    status = "연결 실패로 종료" if dead else "정상 종료"
    print(f"[rtsp_test] {status} - 총 재연결 {reconnects}회, 끊김 {stalls}회, "
          f"실행 시간 {time.time() - start:.0f}초", flush=True)


if __name__ == "__main__":
    main()
