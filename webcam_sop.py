"""통합 SOP 미니 데모 — 인원 수(N인 1조) + 사람별 보호구(헬멧·보안경) 착용 + 안전구역 침범.

네 모델/검출기를 한 루프에서 돌려 결과를 결합한다.
  - person 검출+추적: yolov8n.pt (COCO person) + ByteTrack -> 사람마다 고유 ID
  - 헬멧 검출: models/helmet_v2_best.pt -> helmet / no_helmet 박스
  - 보안경 검출: models/glasses_v1_best.pt -> glasses / no_glasses 박스 (2026-09-17 통합,
    helmet과 완전히 독립된 규칙 — 둘 중 하나만 미착용해도 각각 따로 위반 확정/알림.
    모델 파일이 없거나 helmet만 쓰고 싶으면 --no-glasses)
  - 안전구역: ArUco 마커 4개로 구역 폴리곤을 매 프레임 재계산 (webcam_zone.py 로직)

"보호구 박스가 보이면 착용"이 아니라, 각 person 박스 안에 helmet/no_helmet(또는
glasses/no_glasses) 박스의 중심점이 들어오는지로 "그 사람이 실제로 썼는가"를 판정한다
(webcam_test.md 한계 1 해결) — 이 매칭 로직(match_ppe_to_persons)은 헬멧·보안경이 공유한다.
안전구역도 마찬가지로 "화면 좌표 고정"이 아니라 마커 위치 기준으로 재계산한다 —
착용형 카메라가 움직여도 구역이 따라오고, 마커가 안 보이면 판정 보류로 침묵한다.
보호구 판정도 동일한 원칙을 따른다 — 각도·거리 문제로 잠깐 helmet/no_helmet 어느 쪽도
못 잡으면(PersonState "미확인") "착용"으로 넘겨짚지 않고 직전 판정을 그대로 유지한다
(2026-09-16 수정). 전에는 "미확인"을 "착용"과 같은 값(False)으로 넘겨서 해제 타이머를
진행시켰기 때문에, 헬멧이 잠깐 프레임 밖으로 나가기만 해도 실제로는 계속 미착용인 위반이
조기에 풀려버렸다.
마커 4개 중 1개가 가려져 3개만 보이면, 평행사변형 근사(대각선 중점이 같다는 성질)로
4번째를 추정해 계속 판정한다 — 화면에 그 모서리는 빈 원(마젠타색)으로 표시되어
"이건 실측이 아니라 추정"임을 구분할 수 있다. --no-zone-estimate 로 끌 수 있다.
준비물(마커 인쇄·배치)은 webcam_zone.py 상단 docstring 참고.

사람 추적 ID도 같은 종류의 문제를 겪는다 — ByteTrack이 매기는 ID가 사람이 잠깐 화면을
벗어나거나 빠르게 움직이면 바뀌는데, 위반 판정(PersonState/ZoneState)이 이 ID를 키로
저장하다 보니 ID가 바뀌면 실제로는 아무것도 해결 안 됐는데 "위반 해제"로 잘못 보고되고
새 ID로 타이머가 처음부터 다시 돈다(2026-09-16 발견, 실전에서 "사람마다 보고 ID가 계속
바뀌면 안 된다"는 문제 제기로 확인). PersonIdentityMemory가 마커와 같은 방식으로
"방금(--id-bridge-gap-sec 이내) 사라진 사람의 마지막 위치 근처에 새 ID가 나타나면 같은
사람으로 이어붙인다" — 완벽한 재식별은 아니고 짧은 순간의 ID 이탈만 버티는 실험적
기능이라, 오작동하면 --no-id-bridge로 끄고 예전처럼 raw ID를 그대로 쓸 수 있다.

규칙 4개, 전부 SustainedLatch(지속 시간 채워야 확정/해제)로 처리한다.
  - N인 1조: 인원 수 != N 이 지속 -> 위반 / N명 복귀 지속 -> 해제 (기획안 5.6절, 기본 N=2/3초)
  - 헬멧 미착용: 특정 사람이 미착용 상태로 지속 -> 위반 / 착용 복귀 지속 -> 해제 (기본 10초)
  - 보안경 미착용: 헬멧과 완전히 독립적으로 동일하게 판정 (기본 10초, --no-glasses로 끌 수 있음)
  - 안전구역 침범: 특정 사람이 구역 안에 지속 -> 위반 / 구역 밖 복귀 지속 -> 해제 (기본 3초)

작업마다 필요 인원 수·지속시간이 다를 수 있어 코드 수정 없이 커맨드라인 인자로 바꾼다:

    python webcam_sop.py --crew 3
    python webcam_sop.py --crew 4 --crew-hold 5 --helmet-hold 15 --zone-hold 5

세부 파라미터는 --help 참고. 나중에 SOP를 JSON으로 구조화하면 이 값들은 명령행 인자 대신
SOP 문서에서 읽어오도록 바뀔 예정 — 지금은 그 전 단계 임시 인터페이스.

push_server.py(Web Push 프로토타입)를 같이 띄워두면 --push-url 로 실제 알림 연동:

    uvicorn push_server:app --port 8000        # 다른 터미널에서 먼저 실행
    python webcam_sop.py --push-url http://localhost:8000/notify

관리자 폰 전용 앱(rtauto_sop_android, FCM)으로 실제 알림을 보내려면 --fcm-token
(또는 DEVICE_TOKEN 환경변수)에 앱 홈 화면에서 복사한 기기 토큰을 준다. service-account.json
(Firebase 서비스 계정 키, gitignore)이 프로젝트 루트에 있어야 함 — send_test_alert.py와
동일한 발송 방식(data-only, notification 페이로드 금지)을 공유한다:

    export DEVICE_TOKEN="앱에서 복사한 토큰"
    python webcam_sop.py --fcm-token "$DEVICE_TOKEN"

--push-url과 --fcm-token은 동시에 켜도 되고(둘 다 발송), 규칙별로 앱이 표시할 등급(level)도
같이 보낸다: crew/zone은 "중대", helmet/glasses는 "주의" (기획안 그림4 등급 구분 반영,
재발송/ACK 스케줄러 자체는 아직 없음 — CLAUDE.md 알림 설계 섹션 참고).

FCM은 확정(kind="alert")뿐 아니라 해제(kind="resolved")도 보낸다 — 둘 다 같은 key(rule:target,
fcm_key() 참고)를 실어서, 앱이 "지금 울리는 경보와 같은 건인지" 맞춰보고 자동으로 알람을
끈다(기획안 5.6절 "해제 조건" — 사람이 확인 버튼을 눌러서가 아니라 동일 검출 경로로 정상
복귀가 재확인됐을 때만 해제되어야 함). 해제 신호는 반복 억제(RepeatThrottle)와 무관하게
항상 보낸다 — 확정이 스로틀에 막혀 폰까지 못 갔던 경우엔 앱에 매칭되는 활성 경보가 없어
조용히 무시될 뿐이고, 실제로 알림이 갔던 경우엔 해제도 반드시 도착해야 알람이 안 꺼진 채
남는 사고를 막을 수 있다. 이 계약(kind/key 필드)은 rtauto_sop_android 쪽
AlertFcmService/AlertPlayer/EventStore와 짝을 이루므로, 필드명을 바꾸려면 그쪽도 같이 고칠 것.

위반이 "새로 확정된 순간"마다 알림을 보낸다 — 해제 후 --repeat-cooldown-min(기본 5분) 안에
같은 유형(규칙+사람)이 다시 걸려도(flapping) **알림은 이제 매번 보낸다**(2026-09-16 정책
변경 — 실사용해보니 "재감지된 실제 위반은 매번 알려야 안전하다"는 게 확인됨). RepeatThrottle의
반복 횟수는 계속 세서 --repeat-threshold(기본 3)회째부터는 "(최근 N분 내 M회 반복)" 문구를
알림 본문에 덧붙이기만 한다 — 발송 자체를 막지는 않는다. 등급별 차등 발송(중대/주의별
재발송·확인)은 아직 없음 — CLAUDE.md 알림 설계 섹션 참고.

모든 위반 확정/해제는 --push-url 설정과 무관하게 events.jsonl 에 기록된다 (기획안 그림3
"엣지 PC 저장" 대응). 규칙 종류(rule)와 상관없이 on_violation_confirmed/resolved 라는
공통 지점을 통해서만 기록·발송하므로, 나중에 새 규칙(위험 자세 등)이 추가돼도 이 두 함수를
그대로 호출하면 되고 로그·알림 코드를 다시 건드릴 필요가 없다. 기록된 이벤트는
view_events.py 로 사람이 읽기 쉽게 요약해서 볼 수 있다.

위반이 확정되는 순간, 그 시점까지의 최근 --clip-sec(기본 10초) 프레임을 clips/ 에 mp4로
저장한다(기획안 그림3/4 "경보 구간 클립(10초)" 대응). --no-clip 으로 끌 수 있다. 클립 쓰기는
동기적이라 그동안 프레임이 잠깐 밀린다 — 몇 초에 한 번 수준의 이벤트 빈도를 전제한 프로토타입
타협이며, 실전엔 별도 스레드로 빼야 한다.

클립 저장은 RepeatThrottle이 게이트한다(2026-09-11 발견·수정, 알림 정책은 2026-09-16에
바뀌었지만 클립은 그대로) — 안 그러면 사람이 구역을 들락날락할 때마다 클립이 매번 새로
쓰여서 디스크·프레임에 "녹화 폭탄"이 된다. --push-url/--fcm-token 없이 써도(알림 자체를
안 쓰는 조합이어도) 이 억제는 항상 작동한다. 즉 확정 로그와 알림은 매번 남지만, 클립만
반복 억제 대상이다.
"""

import argparse
import json
import os
import time
from collections import Counter, deque
from datetime import datetime

import cv2
import numpy as np
import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

PERSON_MODEL_PATH = "yolov8n.pt"
HELMET_MODEL_PATH = "models/helmet_v2_best.pt"
GLASSES_MODEL_PATH = "models/glasses_v1_best.pt"
PERSON_CLASS = 0             # COCO 기준 person
PERSON_CONF = 0.4
HELMET_CONF = 0.5
GLASSES_CONF = 0.25          # webcam_glasses.py 단독 테스트에서 검증된 값
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

DEFAULT_GLASSES_HOLD_SEC = 10.0   # 보안경 미착용 위반 확정/해제 지속 시간 (helmet과 동일하게 시작)
DEFAULT_GLASSES_CLEAR_SEC = 10.0

DEFAULT_ZONE_HOLD_SEC = 3.0       # 구역 침범 확정 지속 시간 (위험요인, 2인1조와 동일하게 시작)
DEFAULT_ZONE_CLEAR_SEC = 3.0

DEFAULT_ID_BRIDGE_GAP_SEC = 2.0   # 사람이 사라진 뒤 이 시간(초) 안에 새 추적 ID가 나타나면 같은 사람으로 이어붙임
DEFAULT_ID_BRIDGE_DIST_PX = 120   # 마지막 위치에서 이 픽셀 반경 안이어야 같은 사람으로 인정

DEFAULT_REPEAT_COOLDOWN_MIN = 5.0  # 해제 후 이 시간(분) 안에 같은 위반이 다시 걸리면 "반복"으로 간주
DEFAULT_REPEAT_THRESHOLD = 3       # 반복이 이 횟수에 도달하면 그때 요약 알림 1번만 발송

EVENTS_LOG_PATH = "events.jsonl"   # 위반 확정/해제 이력. 알림 설정과 무관하게 항상 기록됨

CLIP_DIR = "clips"                 # 경보 구간 클립 저장 폴더 (그림3/4 "경보 구간 클립(10초)" 대응)
DEFAULT_CLIP_SEC = 10.0            # 위반 확정 시점까지의 최근 N초를 클립으로 저장

# 관리자 폰 전용 앱(rtauto_sop_android)으로 FCM 발송할 때 쓰는 설정. send_test_alert.py와 동일.
FCM_PROJECT_ID = "rtauto-sop"
FCM_SERVICE_ACCOUNT_FILE = "service-account.json"
FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
FCM_LEVEL_BY_RULE = {"crew": "중대", "zone": "중대", "helmet": "주의", "glasses": "주의"}   


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
    p.add_argument("--glasses-hold", type=float, default=DEFAULT_GLASSES_HOLD_SEC,
                    help=f"보안경 미착용 위반 확정까지 지속 시간(초) (기본 {DEFAULT_GLASSES_HOLD_SEC})")
    p.add_argument("--glasses-clear", type=float, default=DEFAULT_GLASSES_CLEAR_SEC,
                    help=f"보안경 미착용 위반 해제까지 지속 시간(초) (기본 {DEFAULT_GLASSES_CLEAR_SEC})")
    p.add_argument("--no-glasses", action="store_true",
                    help="glasses_v1 모델을 안 쓰고 보안경 판정을 끔 (모델 파일이 없거나 "
                         "helmet만 확인하고 싶을 때)")
    p.add_argument("--zone-hold", type=float, default=DEFAULT_ZONE_HOLD_SEC,
                    help=f"안전구역 침범 확정까지 지속 시간(초) (기본 {DEFAULT_ZONE_HOLD_SEC})")
    p.add_argument("--zone-clear", type=float, default=DEFAULT_ZONE_CLEAR_SEC,
                    help=f"안전구역 침범 해제까지 지속 시간(초) (기본 {DEFAULT_ZONE_CLEAR_SEC})")
    p.add_argument("--no-zone", action="store_true",
                    help="마커를 준비 못 했을 때 안전구역 판정을 끄고 인원수+보호구만 실행")
    p.add_argument("--no-zone-estimate", action="store_true",
                    help="마커 3개(1개 가림)일 때 평행사변형 근사로 4번째를 추정하는 기능을 끄고, "
                         "예전처럼 4개 다 보여야만 구역을 판정. 추정이 못 미더울 때 검증용")
    p.add_argument("--no-id-bridge", action="store_true",
                    help="사람이 잠깐 화면을 벗어나거나 빠르게 움직여도 같은 사람으로 이어붙이는 "
                         "기능(PersonIdentityMemory)을 끄고, ByteTrack이 매긴 추적 ID를 그대로 "
                         "씀. 이어붙이기가 엉뚱한 사람끼리 잘못 이어붙이는 등 오작동할 때 대피용"
                         "(실험적 기능, 2026-09-16 추가)")
    p.add_argument("--id-bridge-gap-sec", type=float, default=DEFAULT_ID_BRIDGE_GAP_SEC,
                    help=f"사람이 사라진 뒤 이 시간(초) 안에 새 추적 ID가 나타나면 같은 사람으로 "
                         f"이어붙임 (기본 {DEFAULT_ID_BRIDGE_GAP_SEC})")
    p.add_argument("--id-bridge-dist-px", type=float, default=DEFAULT_ID_BRIDGE_DIST_PX,
                    help=f"마지막 위치에서 이 픽셀 반경 안이어야 같은 사람으로 인정 (기본 "
                         f"{DEFAULT_ID_BRIDGE_DIST_PX}, 웹캠 해상도·거리에 따라 조정 필요할 수 있음)")
    p.add_argument("--push-url", type=str, default=None,
                    help="위반 '확정' 순간(재발 아님, 새로 걸릴 때만) push_server.py의 /notify로 "
                         "POST 요청. 예: http://localhost:8000/notify. 생략하면 알림 전송 안 함")
    p.add_argument("--fcm-token", type=str, default=os.environ.get("DEVICE_TOKEN", ""),
                    help="rtauto_sop_android 앱 홈 화면에서 복사한 FCM 기기 토큰. 주면 위반 '확정' "
                         "순간 실제 폰에 알림 발송(send_test_alert.py와 동일한 발송 방식). "
                         "DEVICE_TOKEN 환경변수로 줘도 됨. service-account.json 필요")
    p.add_argument("--repeat-cooldown-min", type=float, default=DEFAULT_REPEAT_COOLDOWN_MIN,
                    help=f"해제 후 이 시간(분) 안에 같은 위반이 다시 걸리면 반복으로 간주해 "
                         f"클립 저장은 생략(알림은 매번 그대로 발송) (기본 {DEFAULT_REPEAT_COOLDOWN_MIN})")
    p.add_argument("--repeat-threshold", type=int, default=DEFAULT_REPEAT_THRESHOLD,
                    help=f"반복 횟수가 이 값에 도달하면 그때 클립 저장 재개 + 알림 문구에 "
                         f"반복 횟수 표시 (기본 {DEFAULT_REPEAT_THRESHOLD})")
    p.add_argument("--clip-sec", type=float, default=DEFAULT_CLIP_SEC,
                    help=f"위반 확정 시 저장할 경보 구간 클립 길이(초) (기본 {DEFAULT_CLIP_SEC})")
    p.add_argument("--no-clip", action="store_true",
                    help="경보 구간 클립 저장을 끔 (디스크 아끼고 싶을 때)")
    return p.parse_args()


def send_push(push_url, title, body):
    """push_server.py /notify 로 알림 발송. 실패해도 메인 루프는 계속 돈다(프로토타입이므로)."""
    if not push_url:
        return
    try:
        requests.post(push_url, json={"title": title, "body": body}, timeout=1.5)
    except Exception as e:
        print(f"[push] 알림 발송 실패: {e}")


_fcm_credentials = None   # 모듈 전역 캐시 — 매번 파일에서 다시 읽지 않고 토큰 만료 시에만 갱신


def _get_fcm_access_token():
    global _fcm_credentials
    if _fcm_credentials is None:
        _fcm_credentials = service_account.Credentials.from_service_account_file(
            FCM_SERVICE_ACCOUNT_FILE, scopes=FCM_SCOPES
        )
    if not _fcm_credentials.valid:
        _fcm_credentials.refresh(GoogleAuthRequest())
    return _fcm_credentials.token


def fcm_key(rule, target):
    """rule+target을 앱과 공유하는 하나의 문자열 키로 합친다 (예: "helmet:7", "crew:None").
    확정(alert) 메시지와 해제(resolved) 메시지가 같은 위반을 가리키는지 앱이 이 값으로
    맞춰본다 — rtauto_sop_android의 AlertPlayer.currentKey/EventStore.resolveByKey 참고."""
    return f"{rule}:{target}"


def send_fcm(token, title, body, level="중대", kind="alert", key=None):
    """rtauto_sop_android 앱으로 FCM data-only 메시지 발송 — send_test_alert.py와 동일 설계.
    notification 키를 넣지 않아야 앱이 백그라운드/종료 상태여도 AlertFcmService가 항상 호출된다.
    send_push와 같은 정책: 실패해도 메인 루프는 계속 돈다(프로토타입이므로).

    kind="alert"(기본)면 새 경보로 표시+재생, kind="resolved"면 앱이 같은 key로 울리고
    있던 경보를 조용히 멈춘다(기획안 5.6절 — 해제는 사람 확인이 아니라 재감지로만)."""
    if not token:
        return
    try:
        access_token = _get_fcm_access_token()
    except Exception as e:
        print(f"[fcm] 인증 실패 ({FCM_SERVICE_ACCOUNT_FILE} 확인): {e}")
        return
    url = f"https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }
    data = {"title": title, "body": body, "level": level, "kind": kind}
    if key is not None:
        data["key"] = key
    message = {
        "message": {
            "token": token,
            "data": data,
            "android": {"priority": "high"},
        }
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(message), timeout=3)
        if resp.status_code != 200:
            print(f"[fcm] 발송 실패: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[fcm] 발송 실패: {e}")


def log_event(kind, rule, target, detail):
    """위반 확정/해제 이벤트를 events.jsonl 에 한 줄씩 추가한다 (JSON Lines, 사람도 grep 가능).
    기획안 그림3 "엣지 PC 저장" 대응 — 알림(Web Push) 설정과 무관하게 항상 기록한다."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,       # "confirmed" | "resolved"
        "rule": rule,       # "crew" | "helmet" | "zone" | ...
        "target": target,   # 사람 track ID 또는 None(crew처럼 전역인 경우)
        "detail": detail,
    }
    try:
        with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[log] 이벤트 기록 실패: {e}")


class FrameBuffer:
    """최근 window_sec 초의 프레임을 들고 있다가, 위반 확정 시점에 그 구간을
    클립으로 저장할 수 있게 한다 (기획안 그림3/4 "경보 구간 클립(10초)" 대응)."""

    def __init__(self, window_sec):
        self.window_sec = window_sec
        self.buffer = deque()   # (t, frame) — frame은 그 시점의 복사본

    def append(self, frame, now):
        self.buffer.append((now, frame.copy()))
        while self.buffer and now - self.buffer[0][0] > self.window_sec:
            self.buffer.popleft()

    def snapshot(self):
        """현재 버퍼의 (프레임 리스트, 추정 FPS)를 반환. 프레임이 2개 미만이면 빈 리스트."""
        frames = [f for _, f in self.buffer]
        if len(self.buffer) >= 2:
            duration = self.buffer[-1][0] - self.buffer[0][0]
            fps = (len(self.buffer) - 1) / duration if duration > 0 else 10.0
        else:
            frames, fps = [], 10.0
        return frames, fps


def save_clip(frame_buffer, rule, target, now):
    """FrameBuffer 스냅샷을 mp4로 저장하고 파일 경로를 반환 (실패/프레임 없으면 None).
    쓰기 자체는 동기적이라 그동안 메인 루프가 잠깐 멈춘다 — 클립이 몇 초에 한 번 수준으로만
    발생한다는 전제의 프로토타입 타협. 실전엔 별도 스레드로 빼야 프레임이 안 밀린다."""
    frames, fps = frame_buffer.snapshot()
    if not frames:
        return None
    os.makedirs(CLIP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")   # 마이크로초까지 — 같은 초에 여러 건이면 덮어쓰기 방지
    target_str = f"_id{target}" if target is not None else ""
    path = os.path.join(CLIP_DIR, f"{ts}_{rule}{target_str}.mp4")
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), max(fps, 1.0), (w, h))
    try:
        if not writer.isOpened():
            return None
        for f in frames:
            writer.write(f)
    finally:
        writer.release()
    return path


def on_violation_confirmed(args, throttle, frame_buffer, rule, target, title, detail, now):
    """위반이 새로 확정된 순간(상승 엣지)에 호출하는 공통 지점.
    로그(사실 기록)는 항상 남긴다. 클립 저장과 알림 발송은 이제 서로 다르게 게이트한다
    (2026-09-16 정책 변경, 사용자 피드백 — "재감지된 실제 위반은 매번 알려야 안전하다"):

    - **클립 저장은 여전히 RepeatThrottle이 게이트한다** — 안 그러면 사람이 구역을
      들락날락할 때마다 디스크·프레임에 "녹화 폭탄"이 된다 (2026-09-11 발견·수정 그대로 유지).
    - **알림(Push/FCM)은 이제 항상 보낸다** — 예전엔 반복 억제 대상이었지만, 실사용해보니
      "해제됐다가 진짜로 다시 위반이면 폰이 다시 울려야" 안전하다는 게 확인됨. 알림 피로는
      이제 앱 쪽(자동 해제 N건 배지, 다른 활성 위반 펼치기)에서 완화하므로 발송 자체를
      억제할 필요가 줄었다. RepeatThrottle의 반복 카운트(note)는 그대로 계산해 문구에는
      남기되, 발송 여부를 막는 데는 더 이상 쓰지 않는다."""
    log_event("confirmed", rule, target, detail)

    # should_save_clip()은 내부 반복 횟수 카운터를 건드리는 부수효과가 있으므로 반드시 한
    # 번만 호출한다 — 두 번 부르면 카운터가 매번 2씩 늘어 "N회마다 요약" 계산이 틀어진다.
    ok, note = throttle.should_save_clip((rule, target), now)
    full_detail = detail + (f" {note}" if note else "")

    if ok and not args.no_clip:
        clip_path = save_clip(frame_buffer, rule, target, now)
        if clip_path:
            log_event("clip_saved", rule, target, clip_path)

    if args.push_url:
        send_push(args.push_url, title, full_detail)
    if args.fcm_token:
        send_fcm(args.fcm_token, title, full_detail, level=FCM_LEVEL_BY_RULE.get(rule, "중대"),
                 kind="alert", key=fcm_key(rule, target))


def on_violation_resolved(args, throttle, rule, target, detail, now):
    """위반이 해제된 순간(하강 엣지)에 호출하는 공통 지점.
    push_url 유무와 무관하게 항상 mark_resolved 해야 스로틀이 클립까지 제대로 게이트한다.

    FCM 해제 신호는 반복 억제(RepeatThrottle)와 무관하게 항상 보낸다 — 확정 알림이 스로틀에
    막혀 폰까지 못 갔던 경우엔(앱에 매칭되는 활성 경보가 없어) 조용히 무시될 뿐이고, 실제로
    알림이 갔던 경우엔 반드시 해제 신호도 도착해야 앱의 알람이 계속 울린 채 안 꺼지는 사고를
    막을 수 있다(기획안 5.6절 "해제 조건" — 사람의 확인이 아니라 재감지로만 해제)."""
    log_event("resolved", rule, target, detail)
    throttle.mark_resolved((rule, target), now)
    if args.fcm_token:
        send_fcm(args.fcm_token, "위반 해제", detail, kind="resolved", key=fcm_key(rule, target))


class RepeatThrottle:
    """같은 위반이 해제됐다가 cooldown_min 안에 다시 걸리는 "반복(flapping)"의 반복 횟수를
    센다. 원래는 클립 저장뿐 아니라 알림까지 같이 억제했지만(2026-09-11), 실사용해보니
    "재감지된 실제 위반은 매번 알려야 안전하다"는 게 확인돼 **알림은 이제 매번 보낸다**
    (2026-09-16 정책 변경, on_violation_confirmed 참고). 알림 피로는 이제 앱 쪽(자동 해제
    N건 배지, 다른 활성 위반 펼치기)에서 완화한다. 지금 이 클래스가 실제로 게이트하는 건
    **클립 저장뿐**이다 — 안 그러면 사람이 안전구역을 들락날락할 때마다 클립이 매번 새로
    쓰여서 디스크·프레임에 "녹화 폭탄"이 된다.
      - 오랜만(또는 처음)의 위반은 클립도 저장
      - 최근 해제됐다가 금방 다시 걸리면 클립 없이 반복 횟수만 누적(알림은 그래도 보냄)
      - 반복이 threshold에 도달하면 그때 클립도 다시 저장하고, 알림 문구에도
        "(최근 N분 내 M회 반복)"을 덧붙임
    key로 규칙 종류+대상(사람 ID 등)을 조합해서 쓴다 — 예: ("helmet", 3), ("crew", None)."""

    def __init__(self, cooldown_sec, threshold):
        self.cooldown_sec = cooldown_sec
        self.threshold = threshold
        self.last_resolved = {}   # key -> 마지막으로 해제된 시각
        self.repeat_count = {}    # key -> 이번 억제 구간 동안 쌓인 반복 횟수

    def should_save_clip(self, key, now):
        """위반이 새로 걸린 순간(상승 엣지)에 호출. (클립을 저장할지 여부, 안내 문구 또는
        None) 반환 — 2026-09-16까지는 should_notify라는 이름이었지만, 알림은 이제 이
        반환값과 무관하게 항상 나가고 클립 저장만 게이트하므로 이름을 맞춰 바꿨다.
        반환값의 note는 클립 여부와 무관하게 알림 문구에 항상 덧붙는다."""
        last = self.last_resolved.get(key)
        if last is None or now - last > self.cooldown_sec:
            self.repeat_count[key] = 0
            return True, None
        self.repeat_count[key] = self.repeat_count.get(key, 0) + 1
        if self.repeat_count[key] >= self.threshold:
            n = self.repeat_count[key]
            self.repeat_count[key] = 0   # 요약 보냈으니 다음 구간을 위해 리셋
            return True, f"(최근 {self.cooldown_sec / 60:.0f}분 내 {n}회 반복)"
        return False, None

    def mark_resolved(self, key, now):
        """위반이 해제된 순간(하강 엣지)에 호출."""
        self.last_resolved[key] = now


try:
    _FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 20)
    _FONT_SMALL = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 16)
    _FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 30)
except OSError:
    _FONT = _FONT_SMALL = _FONT_BIG = ImageFont.load_default()

HELMET_LABELS = {0: "helmet", 1: "no_helmet"}
GLASSES_LABELS = {0: "glasses", 1: "no_glasses"}


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
    """트랙 ID 하나(사람 한 명)의 보호구 착용 상태 이력 + 위반 판정.
    마커가 안 보여 판정 불가한 프레임(None)은 이력에서 제외하고, latch도 갱신하지 않는다
    (판정 보류 — ZoneState와 동일 원칙, 2026-09-16 수정). 그 전까지는 "미확인"을 "착용"과
    똑같이 취급해 해제 타이머를 진행시켜서, 헬멧이 잠깐 화면 밖으로 나가거나 각도상
    검출이 안 잡히기만 해도 실제로는 계속 미착용인데 위반이 조기에 풀려버리는 문제가 있었다."""

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
        if not votes:
            return "미확인", self.latch.latched   # 최근 창에 정보 없음 -> 모름, latch 동결
        stable = Counter(votes).most_common(1)[0][0]
        violation = self.latch.update(stable == "미착용", now)
        return stable, violation


def carry_forward_violations(states, seen_pids, violation_ids):
    """이번 프레임에 재검출되지 않은 pid라도, 마지막으로 확인된 위반 상태(latch.latched)가
    True면 위반 목록에 계속 포함시킨다. helmet_violation_ids/zone_violation_ids는 매 프레임
    person_items를 순회하며 새로 채워지는데, 헬멧을 쓰려고 손을 머리로 올리는 등 순간적으로
    person 검출/추적이 끊기면(--*-clear 초와 무관하게) 그 프레임엔 pid가 person_items에
    아예 없어서 곧바로 위반 목록에서 빠지고 "해제"로 오판되는 버그가 있었다(2026-09-17,
    사용자 발견 — 헬멧 쓰자마자 즉시 자동해제). 여기서 이어붙여두면 실제 해제는 재검출된
    뒤 pstate.update()가 clear_sec만큼 "착용"을 확인해야만 일어난다 — 사람이 계속 안 보이면
    person_states/zone_states 자체가 30초 뒤 정리되면서 그때 비로소 해제된다."""
    for pid, state in states.items():
        if pid not in seen_pids and state.latch.latched:
            violation_ids.add(pid)


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


class PersonIdentityMemory:
    """ByteTrack이 매기는 추적 ID(raw id)가 사람이 잠깐 화면을 벗어나거나 빠르게 움직이면
    바뀌는 문제를 완화한다 (2026-09-16, 사용자 발견 — 실제 웹캠 테스트에서 ID가 계속 바뀌며
    위반이 해결 안 됐는데도 "해제"로 잘못 보고되고, 매번 새 사람처럼 타이머가 처음부터
    다시 도는 문제 확인).

    MarkerMemory("마커가 잠깐 안 보여도 최근 위치를 기억해서 버틴다")와 같은 철학 —
    완벽한 재식별(ReID)이 아니라 "짧은 순간의 ID 이탈"만 이어붙이는 가벼운 다리(bridge)다.
    방금(max_gap_sec 이내) 사라진 사람의 마지막 발 위치(foot_point) 근처에 새 raw id가
    나타나면 같은 사람(canonical id)으로 취급 — 이후 person_states/zone_states/알림의
    key가 전부 이 canonical id를 쓰므로, 위반 확정→해제 타이머와 이력이 ID 변경을
    관통해 그대로 이어진다.

    한계: 여러 사람이 겹쳐 있거나 오래(max_gap_sec 이상) 사라지면 못 잡는다 — 그 경우는
    실제로 새 사람일 수도 있으니 새 canonical id를 새로 발급하는 게 맞다. --no-id-bridge로
    끄면 예전처럼 raw id를 그대로 canonical id로 쓴다(이 기능이 오작동할 때의 대피용)."""

    def __init__(self, max_gap_sec=2.0, max_dist_px=120):
        self.max_gap_sec = max_gap_sec
        self.max_dist_px = max_dist_px
        self.raw_to_canonical = {}   # raw id -> canonical id (한 번 정해지면 계속 유지)
        self.canonical_pos = {}      # canonical id -> (foot_point, 마지막으로 본 시각)

    def resolve_frame(self, person_items, now):
        """이번 프레임의 (raw_id, box) 목록을 (canonical_id, box) 목록으로 바꿔서 반환한다."""
        used_canonicals = set()
        resolved = []
        unresolved = []

        for raw_id, box in person_items:
            canonical = self.raw_to_canonical.get(raw_id)
            if canonical is not None and canonical not in used_canonicals:
                used_canonicals.add(canonical)
                resolved.append((canonical, box))
            else:
                unresolved.append((raw_id, box))

        for raw_id, box in unresolved:
            foot = foot_point(box)
            best_canonical, best_dist = None, None
            for canonical, (last_foot, last_t) in self.canonical_pos.items():
                if canonical in used_canonicals or now - last_t > self.max_gap_sec:
                    continue   # 이번 프레임에 이미 다른 raw id가 쓰는 중이거나 너무 오래 사라졌음
                dist = ((foot[0] - last_foot[0]) ** 2 + (foot[1] - last_foot[1]) ** 2) ** 0.5
                if dist <= self.max_dist_px and (best_dist is None or dist < best_dist):
                    best_canonical, best_dist = canonical, dist
            canonical = best_canonical if best_canonical is not None else raw_id
            self.raw_to_canonical[raw_id] = canonical
            used_canonicals.add(canonical)
            resolved.append((canonical, box))

        for canonical, box in resolved:
            self.canonical_pos[canonical] = (foot_point(box), now)

        # 오래(30초) 안 보인 canonical은 정리 — person_states 정리 주기와 맞춤
        stale = [c for c, (_, t) in self.canonical_pos.items() if now - t > 30]
        for c in stale:
            del self.canonical_pos[c]

        return resolved


def match_ppe_to_persons(person_items, ppe_boxes, labels, positive_label):
    """보호구(helmet/glasses 등) 박스 중심이 들어있는 person 박스에 배정 — 착용/미착용
    2클래스 검출기라면 전부 이 함수 하나로 재사용 가능(webcam_test.md 한계 1: "검출=착용"이
    아니라 person 박스와의 공간 관계로 판정). 여러 person과 겹치면 가장 작은(가까운) person
    박스 우선, 중복 매칭 시 confidence 높은 쪽. [labels]는 클래스 인덱스->라벨 문자열
    (예: HELMET_LABELS), [positive_label]은 그중 "착용"에 해당하는 라벨(예: "helmet")."""
    assigned = {pid: None for pid, _ in person_items}   # pid -> (label, conf)
    for pb in ppe_boxes:
        px1b, py1b, px2b, py2b = box_xyxy(pb)
        cx, cy = (px1b + px2b) / 2, (py1b + py2b) / 2
        label = labels.get(int(pb.cls[0]), "?")
        conf = float(pb.conf[0])

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
        out[pid] = "착용" if (val and val[0] == positive_label) else ("미착용" if val else None)
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


def combined_color(helmet_stat, glasses_stat, zone_stat, is_violation):
    """사람 박스/라벨 색: 위반 확정=빨강, 위반 소지(미착용 또는 구역안)=주황,
    전부 정상 확인됨=초록, 전부 모름=회색."""
    if is_violation:
        return (220, 30, 30)
    if helmet_stat == "미착용" or glasses_stat == "미착용" or zone_stat == "안":
        return (230, 150, 0)
    if helmet_stat == "미확인" and glasses_stat == "미확인" and zone_stat == "미확인":
        return (140, 140, 140)
    return (0, 170, 0)


CORNER_DOT_COLOR = {
    "live": (0, 255, 0),        # 이번 프레임에 실제로 검출
    "memory": (255, 160, 0),    # 최근(STALE_SEC 이내) 기억한 위치 사용
    "estimated": (255, 0, 190), # 3개로 평행사변형 근사 추정
}


def draw_overlay(bgr, zone_poly, zone_status, marker_ids_seen, person_items,
                  helmet_status, glasses_status, zone_person_status,
                  helmet_violation_ids, glasses_violation_ids, zone_violation_ids,
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
        g_stat = glasses_status.get(pid, "미확인")
        z_stat = zone_person_status.get(pid, "미확인") if zone_enabled else "미확인"
        violated = pid in helmet_violation_ids or pid in glasses_violation_ids or pid in zone_violation_ids
        color = combined_color(h_stat, g_stat, z_stat, violated)

        tags = []
        if pid in helmet_violation_ids:
            tags.append("헬멧위반")
        if pid in glasses_violation_ids:
            tags.append("보안경위반")
        if pid in zone_violation_ids:
            tags.append("구역위반")
        suffix = " " + "/".join(tags) if tags else ""
        tag = f"ID{pid} 헬멧:{h_stat} 보안경:{g_stat}"
        if zone_enabled:
            tag += f" 구역:{z_stat}"
        tag += suffix

        width = 3 if violated else 2
        d.rectangle([x1, y1, x2, y2], outline=color, width=width)
        d.rectangle([x1, max(0, y1 - 22), x1 + 9 * len(tag), y1], fill=color)
        d.text((x1 + 2, max(0, y1 - 21)), tag, font=_FONT_SMALL, fill=(255, 255, 255))

    top2 = f"마커 인식: {marker_ids_seen} / 필요 {ZONE_MARKER_ORDER}" if zone_enabled else "안전구역 판정 꺼짐 (--no-zone)"
    d.text((12, 34), top2, font=_FONT_SMALL, fill=(0, 255, 0) if zone_poly else (255, 120, 0))

    w, h = img.size
    bands = [(crew_banner, crew_rgb, _FONT_BIG, 56)]
    if helmet_violation_ids:
        text = "헬멧 미착용 위반: " + ", ".join(f"ID{i}" for i in sorted(helmet_violation_ids))
        bands.append((text, (200, 60, 0), _FONT, 26))
    if glasses_violation_ids:
        text = "보안경 미착용 위반: " + ", ".join(f"ID{i}" for i in sorted(glasses_violation_ids))
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
          f"헬멧 미착용 (확정 {args.helmet_hold}초/해제 {args.helmet_clear}초), "
          + (f"보안경 미착용 (확정 {args.glasses_hold}초/해제 {args.glasses_clear}초), "
             if not args.no_glasses else "보안경 판정 꺼짐(--no-glasses), ")
          + (f"안전구역 침범 (확정 {args.zone_hold}초/해제 {args.zone_clear}초)"
             if zone_enabled else "안전구역 판정 꺼짐"))
    print(f"ID 이어붙이기(실험적): "
          + (f"켜짐 (사라진 뒤 {args.id_bridge_gap_sec}초/{args.id_bridge_dist_px}px 안이면 같은 사람)"
             if not args.no_id_bridge else "꺼짐 (--no-id-bridge, ByteTrack raw id 그대로 사용)"))
    if args.push_url or args.fcm_token:
        channels = []
        if args.push_url:
            channels.append(f"Web Push({args.push_url})")
        if args.fcm_token:
            channels.append(f"FCM(폰 토큰 등록됨, 앞 12자 {args.fcm_token[:12]}...)")
        print(f"알림: {' + '.join(channels)} (매 확정마다 발송, 억제 없음) | "
              f"클립 반복 억제: {args.repeat_cooldown_min}분 안 재발 시 생략, "
              f"{args.repeat_threshold}회마다 재개")
    print(f"경보 구간 클립: {'끔' if args.no_clip else f'{args.clip_sec}초 -> {CLIP_DIR}/'} | "
          f"이벤트 로그: {EVENTS_LOG_PATH}")

    person_model = YOLO(PERSON_MODEL_PATH)
    helmet_model = YOLO(HELMET_MODEL_PATH)
    glasses_model = YOLO(GLASSES_MODEL_PATH) if not args.no_glasses else None
    detector = cv2.aruco.ArucoDetector(ARUCO_DICT, cv2.aruco.DetectorParameters())

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return
    _run(cap, person_model, helmet_model, glasses_model, detector, args, zone_enabled)


def _run(cap, person_model, helmet_model, glasses_model, detector, args, zone_enabled):
    count_history = deque()          # (t, raw_count) — 인원 수 안정화
    crew_rule = SustainedLatch(args.crew_hold, args.crew_clear)
    person_states = {}               # canonical_id -> PersonState (헬멧)
    glasses_states = {}              # canonical_id -> PersonState (보안경, helmet과 별개 규칙)
    zone_states = {}                 # canonical_id -> ZoneState (안전구역)
    marker_memory = MarkerMemory(STALE_SEC, allow_estimate=not args.no_zone_estimate)
    identity_memory = PersonIdentityMemory(args.id_bridge_gap_sec, args.id_bridge_dist_px)
    prev_t = time.time()

    # 위반 확정/해제는 항상 events.jsonl 에 기록되고, 알림은 그중 "새로 걸린 순간"에만 보낸다.
    # 해제 후 금방 다시 걸리는 반복(flapping)은 RepeatThrottle이 억제 — 매번 알리지 않고
    # 누적하다 threshold 넘으면 요약 1번만
    prev_crew_violation = False
    prev_helmet_violation_ids = set()
    prev_glasses_violation_ids = set()
    prev_zone_violation_ids = set()
    repeat_throttle = RepeatThrottle(args.repeat_cooldown_min * 60, args.repeat_threshold)
    frame_buffer = FrameBuffer(args.clip_sec)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("카메라 프레임을 읽을 수 없습니다.")
            break

        now = time.time()
        if not args.no_clip:
            frame_buffer.append(frame, now)

        person_res = person_model.track(
            frame, classes=[PERSON_CLASS], conf=PERSON_CONF, imgsz=IMGSZ,
            persist=True, tracker=TRACKER, verbose=False,
        )
        person_items = [
            (int(b.id), box_xyxy(b)) for b in person_res[0].boxes if b.id is not None
        ]
        # ByteTrack의 raw id가 사람이 잠깐 화면을 벗어나거나 빠르게 움직이면 바뀌는 문제를
        # 이어붙인다 — 이후 모든 로직(헬멧 매칭, 구역 판정, 규칙 엔진, 알림)은 이 canonical
        # id를 사람 식별자로 쓴다. --no-id-bridge로 끄면 raw id를 그대로 쓴다.
        if not args.no_id_bridge:
            person_items = identity_memory.resolve_frame(person_items, now)

        helmet_res = helmet_model(frame, conf=HELMET_CONF, verbose=False)
        frame_helmet_status = match_ppe_to_persons(person_items, helmet_res[0].boxes, HELMET_LABELS, "helmet")

        if glasses_model is not None:
            glasses_res = glasses_model(frame, conf=GLASSES_CONF, verbose=False)
            frame_glasses_status = match_ppe_to_persons(person_items, glasses_res[0].boxes, GLASSES_LABELS, "glasses")
        else:
            frame_glasses_status = {}

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

        # 사람별 보호구(헬멧/보안경) + 안전구역 상태 갱신
        helmet_status, glasses_status, zone_status = {}, {}, {}
        helmet_violation_ids, glasses_violation_ids, zone_violation_ids = set(), set(), set()
        for pid, box in person_items:
            pstate = person_states.setdefault(pid, PersonState(args.helmet_hold, args.helmet_clear))
            h_stable, h_violated = pstate.update(frame_helmet_status.get(pid), now)
            helmet_status[pid] = h_stable
            if h_violated:
                helmet_violation_ids.add(pid)

            if glasses_model is not None:
                gstate = glasses_states.setdefault(pid, PersonState(args.glasses_hold, args.glasses_clear))
                g_stable, g_violated = gstate.update(frame_glasses_status.get(pid), now)
                glasses_status[pid] = g_stable
                if g_violated:
                    glasses_violation_ids.add(pid)

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

        # 이번 프레임에 재검출 안 된 사람(occlusion, 추적 끊김)의 기존 위반은 그대로 이어감 —
        # --helmet-clear/--glasses-clear/--zone-clear 하이스터리시스를 건너뛰고 즉시 해제되는 걸 막는다.
        seen_pids = {pid for pid, _ in person_items}
        carry_forward_violations(person_states, seen_pids, helmet_violation_ids)
        if glasses_model is not None:
            carry_forward_violations(glasses_states, seen_pids, glasses_violation_ids)
        if zone_enabled:
            carry_forward_violations(zone_states, seen_pids, zone_violation_ids)

        for pid in [p for p, s in person_states.items() if now - s.last_seen > 30]:
            del person_states[pid]
        for pid in [p for p, s in glasses_states.items() if now - s.last_seen > 30]:
            del glasses_states[pid]
        for pid in [p for p, s in zone_states.items() if now - s.last_seen > 30]:
            del zone_states[pid]

        if crew_violation:
            elapsed = int(now - crew_rule.latched_at)
            crew_banner, crew_rgb = f"{args.crew}인 1조 위반 ({elapsed}초)", (200, 0, 0)
        elif stable_count == args.crew:
            crew_banner, crew_rgb = f"정상 ({args.crew}인 1조)", (0, 140, 0)
        else:
            crew_banner, crew_rgb = f"감시 중 (인원 {stable_count})", (200, 130, 0)

        # 위반 확정/해제는 알림 설정과 무관하게 항상 이벤트 로그에 남는다 (on_violation_* 내부에서
        # push_url 있을 때만 실제 발송까지 함). 새 규칙이 추가돼도 이 호출 패턴만 따라가면 된다.
        if crew_violation and not prev_crew_violation:
            on_violation_confirmed(args, repeat_throttle, frame_buffer, "crew", None,
                                    "중대 편차 발생", f"{args.crew}인 1조 위반", now)
        for pid in helmet_violation_ids - prev_helmet_violation_ids:
            on_violation_confirmed(args, repeat_throttle, frame_buffer, "helmet", pid,
                                    "보호구 미착용(헬멧)", f"작업자 ID{pid} 헬멧 미착용 지속", now)
        for pid in glasses_violation_ids - prev_glasses_violation_ids:
            on_violation_confirmed(args, repeat_throttle, frame_buffer, "glasses", pid,
                                    "보호구 미착용(보안경)", f"작업자 ID{pid} 보안경 미착용 지속", now)
        for pid in zone_violation_ids - prev_zone_violation_ids:
            on_violation_confirmed(args, repeat_throttle, frame_buffer, "zone", pid,
                                    "안전구역 침범", f"작업자 ID{pid} 구역 내 위치", now)

        if prev_crew_violation and not crew_violation:
            on_violation_resolved(args, repeat_throttle, "crew", None,
                                   f"{args.crew}인 1조 위반 해제", now)
        for pid in prev_helmet_violation_ids - helmet_violation_ids:
            on_violation_resolved(args, repeat_throttle, "helmet", pid,
                                   f"작업자 ID{pid} 헬멧 착용 복귀", now)
        for pid in prev_glasses_violation_ids - glasses_violation_ids:
            on_violation_resolved(args, repeat_throttle, "glasses", pid,
                                   f"작업자 ID{pid} 보안경 착용 복귀", now)
        for pid in prev_zone_violation_ids - zone_violation_ids:
            on_violation_resolved(args, repeat_throttle, "zone", pid,
                                   f"작업자 ID{pid} 구역 밖 복귀", now)

        prev_crew_violation = crew_violation
        prev_helmet_violation_ids = set(helmet_violation_ids)
        prev_glasses_violation_ids = set(glasses_violation_ids)
        prev_zone_violation_ids = set(zone_violation_ids)

        annotated = draw_overlay(
            frame, zone_poly_i, zone_corner_status, marker_ids_seen, person_items,
            helmet_status, glasses_status, zone_status,
            helmet_violation_ids, glasses_violation_ids, zone_violation_ids,
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
