# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code를 위한 안내입니다.

## 프로젝트 개요

**알티자동화(RT Automation)** 의 "작업자 행동인식 기반 SOP 준수 지원 시스템" 시범 과제 중
**AI 모델 학습/검증 파트**의 작업 저장소입니다. 전체 시스템이 아니라, 그 시스템에 들어갈
객체 검출 모델을 준비하는 실험 코드가 여기에 있습니다.

- 작성자: 신민하 (알티자동화)
- 저장소: https://github.com/minha8680/rtauto_sop (**public**)
- 현재 단계: **감시단원 카메라 채널의 3개 판정 항목(N인 1조 / 보호구 착용 / 안전구역 침범)을
  `webcam_sop.py` 하나로 통합 완료** + Web Push 알림 프로토타입(`push_server.py`) 동작 확인.
  작업자 카메라 채널(항목·순서, 급소포인트)은 **SOP 문서가 없어 착수 불가**. 다음은 SOP 문서화.
- 기획안 원문(PDF/DOCX)은 사용자 바탕화면에 있고 저장소에는 없다(`*.docx`/`*.pdf` gitignore).
  안전구역 설정 방식은 기획안에 없던 내용이라 "5.7 안전구역 설정 방식" 절을 추가한
  사본을 만들어 둠: `바탕화면/장비_구매_기획안_1안_최종본_안전구역설정방식추가.docx`

### 전체 시스템에서 이 저장소의 위치

전체 시스템은 작업자 2인 1조 세정기 작업을 바디캠 2대로 촬영 → 엣지 PC가 SOP와 대조 →
편차 확정 시 작업자 헤드셋 음성 + 관리자 휴대폰 Web Push로 통보하는 구조다.
자세한 배경은 [README.md](README.md) 참고.

- **AI는 객체 검출·추적·음성 인식(STT)에만 사용**한다. 편차 판정은 규칙(rule) 기반.
- 사람·안전보호구 같은 범용 객체는 **공개 사전학습 모델을 그대로 사용**하는 게 기본 방침.
  세정기 특유 부품/동작 등 공개 모델이 못 다루는 항목만 소량 현장 영상으로 fine-tuning.
- 이 저장소의 헬멧 검출 실험은 그 "보호구 착용" 항목의 사전 검증에 해당한다.
- 라이선스 방침: 검출 모델은 **Apache-2.0 계열**(예: YOLOX)을 지향. AGPL-3.0(YOLO Ultralytics
  기본 라이선스) 상용 배포 제약을 피하는 게 목표. 현재 실험 코드는 `ultralytics`를 쓰지만,
  실제 제품 통합 시 모델 프레임워크는 재검토 대상.

### 카메라 2채널 — 항목별 담당이 다르다 (중요)

기획안 표 1 기준. **지금 구현된 건 전부 감시단원 채널이다.** 새 기능을 붙일 때 "이게 어느
카메라 항목인지" 먼저 확인할 것.

| SOP 항목 | 판정 항목 | 담당 카메라 | 현재 |
|---|---|---|---|
| 안전관리대책 | N인 1조 인원 수 | **감시단원** (2~4m) | ✅ `webcam_sop.py` |
| 안전관리대책 | 보호구 착용 | **감시단원** (2~4m) | ✅ `webcam_sop.py` |
| 위험요인 | 안전구역 침범 | **감시단원** (광역) | ✅ `webcam_sop.py` (PoC) |
| 위험요인 | 위험 자세(사다리 끝단) | **감시단원** (광역) | ❌ |
| 항목·순서 | 단계 순서 위반·누락 | **작업자** (근접) | ❌ SOP 필요 |
| 급소포인트 | 필수 동작 누락·확인 생략 | **작업자** (0.8m 이내) | ❌ SOP 필요 |
| STEP별 작업시간 | 표준시간 초과·과속 | 양 카메라 공통 | ❌ SOP 필요 |

즉 `webcam_sop.py` = 사실상 **"감시단원 채널 처리기"**. 나중에 작업자 채널이 생기면 구조를
이렇게 나눠야 한다(단순히 같은 스크립트를 두 번 돌리는 게 아님 — 채널마다 보는 항목과 모델이 다름):

```
채널 A (작업자캠, 근접)   → 손동작·공구·부품 검출 → 단계 순서·급소포인트 판정 ─┐
                                                                              ├→ SOP 상태 기계 → 편차 확정 → 출력
채널 B (감시단원캠, 광역) → person·helmet·구역 검출 → 인원수·보호구·구역 판정 ─┘
                            (= 지금 webcam_sop.py)
```

리팩터링 방향: 지금은 "검출→판정→화면표시"가 한 덩어리라, 나중에 **판정부(SustainedLatch
규칙들)를 채널 처리기에서 떼어내 공통 엔진으로** 옮겨야 한다.

**다행인 점**: 다중 카메라에서 제일 어려운 cross-camera re-ID("A캠 1번 = B캠 3번")는 **안 해도
될 가능성이 높다**. 인원 수는 감시단원 캠만, 단계 순서는 작업자 캠만 보고, 유일한 공통 항목인
STEP 소요시간도 체류시간 기반이라 각 채널이 독립 측정 가능하기 때문.

## 환경

- **OS**: Windows 10, 주 셸은 **Git Bash (MINGW64)**. PowerShell 아님 — 명령을 안내할 때
  Git Bash 문법으로 준다.
- **가상환경 활성화**: `source venv/Scripts/activate` (활성 시 프롬프트에 `(venv)`)
- **로컬 GPU**: NVIDIA GTX 1050 Ti (VRAM 4GB, Pascal). 추론엔 쓸 수 있으나 학습엔 약함.
  로컬 `torch`는 **CPU 빌드**(`2.14.0+cpu`) — `torch.cuda.is_available()` → `False`.
  로컬은 추론(웹캠) 전용, **학습은 Colab에서** 한다.
- **디스크 여유가 적다** (C: ~10GB 대). CUDA torch(~5GB)는 로컬에 설치 시도하다 실패한 이력 있음.
  `pip install` 시 `--no-cache-dir` 를 붙일 것 (pip 캐시가 메모리/디스크를 터뜨린 적 있음).
- Python 패키지는 `venv/`에 설치됨. `requirements.txt`는 아직 없음(만들면 유용).
  설치돼 있는 주요 패키지: `ultralytics`, `torch(cpu)`, `opencv-python`(headless 아님), `roboflow`,
  `python-docx`, `lap`(ByteTrack용), `fastapi`+`uvicorn`+`pywebpush`(Web Push 프로토타입용), `requests`.
  - `opencv-python-headless`가 딸려 들어오면 `cv2.imshow`가 안 된다. headless 제거 후 `opencv-python` 재설치.
  - 콘솔이 **cp949**라 `print()`에 em-dash(—) 같은 비-cp949 문자를 넣으면 `UnicodeEncodeError`가 난다.
    스크립트 출력문엔 일반 하이픈을 쓸 것. 파일 읽기/쓰기는 항상 `encoding="utf-8"` 명시.
  - 한글 파일명을 bash 명령줄로 넘기면 깨진다. 한글 경로가 필요한 작업은 .py 파일로 작성해서 실행할 것.

## 학습 워크플로 (중요)

학습은 **Google Colab (T4 GPU)** 에서 한다. 로컬은 결과물 정리·추론만.

```
Colab: 리포 clone → Roboflow로 데이터셋 다운로드 → 재매핑 → 학습 → files.download()
   ↓  (사용자가 브라우저로 다운로드)
로컬 ~/Downloads/  ← Claude가 여기 직접 접근 가능 (사용자가 채팅에 첨부할 필요 없음)
   ↓  Claude가 이동
models/<name>_best.pt   (gitignore, 로컬/Drive 보관)
docs/<name>/            (results.csv, results.png, confusion_matrix.png → 커밋 가능)
   ↓
로컬 PC에서 git commit + push   ← push는 로컬에서만. Colab에서 직접 push 안 함
```

- 클래스별 P/R/mAP 표는 파일로 안 남고 Colab 콘솔 로그에만 있음 → 필요하면 사용자에게 텍스트 요청,
  또는 `confusion_matrix.png`에서 recall 계산.
- Colab에서 추가로 받으면 좋은 것: `BoxF1_curve.png`(conf 임계값 결정용), `BoxPR_curve.png`, `args.yaml`.

## 저장소 구조

```
rtauto_sop/
├── webcam_sop.py        # ★ 메인 통합 데모 (= 감시단원 채널 처리기)
│                        #   person+helmet_v2+ArUco 구역을 한 루프에서. 3규칙:
│                        #   N인1조(3초) / 보호구 미착용(10초) / 안전구역 침범(3초)
│                        #   --crew, --*-hold, --no-zone, --push-url 로 파라미터화
├── push_server.py       # Web Push 알림 프로토타입 서버(FastAPI). 구독 페이지 + /notify
├── generate_vapid_keys.py  # Web Push용 VAPID 키 생성 (최초 1회)
├── generate_markers.py  # ArUco 마커 4장(TL/TR/BR/BL) 생성 → markers/
├── markers/             # 생성된 마커 PNG (프린트해서 구역 네 모서리에 배치)
├── trackers/bytetrack_person.yaml  # 저FPS(CPU)용 ByteTrack 튜닝 설정
│
│   ── 아래는 단계별 검증용으로 남겨둔 단일 기능 스크립트 (통합본은 webcam_sop.py) ──
├── webcam_helmet.py     # 안전모 착용/미착용만
├── webcam_person.py     # 인원 수+추적+2인1조 규칙만
├── webcam_zone.py       # 안전구역 침범만 (MarkerMemory 원본 구현)
├── debug_aruco.py       # 마커 인식 자체만 진단 (코드 vs 조명/거리 문제 분리용)
├── predict.py           # 학습 가중치로 test 이미지 일괄 추론
│                        # main.py 자리는 비워둠 — 2채널 통합 파이프라인이 생기면 그게 진입점
├── docs/
│   ├── helmet_v1/       # 착용 위주 데이터셋 baseline 결과 (실패 사례)
│   └── helmet_v2/       # 착용/미착용 2클래스 결과 (성공) + webcam_test.md
├── models/              # .gitignore(*.pt) — helmet_v1_best.pt, helmet_v2_best.pt (로컬 전용)
├── datasets/, runs/, venv/          # .gitignore
├── yolov8n.pt                        # 사전학습 가중치 (*.pt로 제외)
├── vapid_private_key.pem            # .gitignore(*.pem) — Web Push 서명 키, 비공개
├── vapid_public_key.txt             # .gitignore — 구독용 공개 키
├── push_subscriptions.json          # .gitignore — 구독자 엔드포인트(개인 기기 토큰)
├── 개발_진행_계획.docx               # .gitignore(*.docx) — 전체 로드맵
├── README.md
└── CLAUDE.md
```

`.gitignore`: `venv/`, `*.pt`, `datasets/`, `runs/`, `.env`, `*.pem`, `vapid_public_key.txt`,
`push_subscriptions.json`, `*.docx`, `*.pdf`, `.idea/`, `.vscode/`

## 학습한 모델

| 모델 | 데이터셋 | 클래스 | 결과 | 파일 |
|---|---|---|---|---|
| helmet_v1 | Roboflow `hard-hat-detection-ws2wk` v1 (668장) | hard hat / no hard hat / not hard hat | mAP50 0.41. 착용 recall 0.91, **미착용 0.00~0.33 (실패)** | `models/helmet_v1_best.pt` |
| **helmet_v2** | Roboflow `joseph-nelson/hard-hat-workers` (~7,000장) | helmet / no_helmet (person 제외) | **mAP50 0.96. 착용 recall 0.97, 미착용 0.95 (성공)** | `models/helmet_v2_best.pt` |

- **핵심 교훈**: helmet_v1과 v2는 학습 설정 동일, **데이터셋만 교체**. 미착용 학습 표본이
  16~64개 → 1,000개 이상으로 늘자 미착용 recall 0.00 → 0.95. "학습량이 아니라 데이터 문제".
- 자세한 지표는 `docs/helmet_v1/metrics.md`, `docs/helmet_v2/metrics.md`,
  웹캠 테스트 평가는 `docs/helmet_v2/webcam_test.md`.

## 프로젝트 완성도 (현실 체크)

**완료**: **감시단원 카메라 채널의 판정 항목 3개 전부**(N인 1조 / 보호구 착용 / 안전구역 침범)를
`webcam_sop.py` 하나로 통합. 안전구역은 알고리즘 **개념 검증(PoC)** 수준. 실제로 있는 것:

- helmet_v2 검출 모델 (재사용 가능한 핵심 자산)
- Colab 학습 파이프라인 (다른 클래스에 재사용)
- person 검출 + ByteTrack 추적 + 공간 매칭(helmet↔person) + `SustainedLatch` 규칙 패턴
  (지속시간 확정/해제, 재사용되는 핵심 로직)
- ArUco 마커로 "카메라가 움직여도 구역을 다시 찾는" 방식 — 웹캠에서 동작 검증됨
- Web Push 알림 프로토타입 — 구독 → 위반 확정 시 실제 브라우저 알림까지 경로 검증됨
- 실험 결과·한계 문서

**아직 없는 것 (= 시스템 본체)**:
- **작업자 카메라 채널 전체** (항목·순서, 급소포인트) — SOP 문서가 없어 착수 불가
- SOP JSON + 규칙 판정 엔진, STEP 소요시간 — 마찬가지로 SOP 문서가 선행 조건
- 2채널 동시 수신·통합 구조 (지금은 단일 카메라 전제)
- 편차 등급(중대/주의/일반) 차등 발송, 알림 반복 억제, 작업 세션(근무시간) 게이팅
- 음성 경로(STT/TTS/헤드셋), 엣지 PC 통합, heartbeat 로직, 위험 자세 검출

**바디캠이 와도 "꽂으면 시스템이 돈다"가 아니다.** `cv2.VideoCapture(0)` → `VideoCapture("rtsp://…")`
한 줄 변경 자체는 쉽지만, RTSP는 버퍼링·지연 관리, 끊김 재연결, 2채널 동시 수신, 3fps 다운샘플링,
SoftAP 무선망 구성이 별도로 필요하다 (며칠짜리). 바디캠 입고의 의미는 **helmet_v2 모델을 실제
현장 거리·화각(2~4m, 안전모 22~35px)에서 검증 시작**할 수 있게 되는 것이다.

**안전구역 PoC도 마찬가지로 "완성"이 아니다.** 지금은 프린트한 종이 마커 + 마커 4개가 전부
보여야만 판정하는 단순 버전. 실전 적용 전 필요한 것: 방수·내구성 있는 마커 재질, 4~10m
거리에서 인식되는 크기 실측, 마커 일부만 보여도 판정하는 보강 로직, 부착 위치 결정.
`webcam_zone.py` 최상단 docstring에 한계 정리돼 있음.

"helmet 검출 = 착용"이 아니라는 점도 중요 (`webcam_test.md` 한계 1). `webcam_sop.py`에서
person/helmet 박스의 공간 관계(박스 안에 중심점 포함)로 이미 해결함 — 새로 만들 때 이 로직
재사용할 것.

**Web Push 프로토타입도 "완성"이 아니다.** localhost 전용(HTTPS 없음)이라 실제 휴대폰에서 받으려면
인증서가 필요하고, 구독 정보는 JSON 파일에 저장(실제론 DB), 기획안 5.5절의 30초 재발송·확인(ACK)
처리·등급별 차등 발송은 미구현.

- **PC 브라우저(localhost:8000)로 구독→발송→수신 전 경로 검증 완료.** 로직 자체는 정상 동작.
- **휴대폰 실제 수신은 미검증** — 시도했으나 막힘: LAN IP(`http://<PC IP>:8000`)는 HTTPS가
  아니라 브라우저가 Push API를 숨겨서 "미지원"으로 보임. 우회하려던 `chrome://flags`의
  insecure-origin 허용도 관리자 휴대폰이 MDM 관리 기기라 접근 자체가 막혀 있었음.
- **다음에 폰으로 확인하려면**: (a) ngrok 등으로 임시 HTTPS 터널 (인터넷 노출 — 진행 전 확인
  필요), (b) 회사 관리 안 받는 개인 폰으로 시도, (c) 엣지 PC에 실제 HTTPS 인증서 붙을 때 같이
  검증(가장 실전에 가까움, 장비 입고 후).

### 알림 설계 — 나중에 반영할 논의 결과 (오탐 피로 방지)

관리자에게 알림이 너무 자주 가면 신뢰를 잃는다(alarm fatigue). 다음이 필요하다는 결론이 났으나
전부 미구현:
1. **등급별 차등 발송** — 기획안 그림 4 목업에 이미 중대/일반/주의 3등급이 있음. 중대(2인1조)만
   30초 재발송, 주의(보호구)는 1회, 일반(표준시간 초과)은 이벤트 목록에만 기록
2. **반복(flapping) 억제** — 해제 후 N분 내 같은 유형 재발생 시 새 알림 대신 누적 카운트,
   임계 초과 시 "반복 발생" 요약 1회 (Phase 6 알림 시스템 만들 때 같이 구현)
3. **작업 세션 게이팅** — 점심·교대 시간엔 규칙 평가 자체를 끔. 카메라를 물리적으로 끄는 건
   비추천(수동 의존·영상 공백). 고정 시간표로 시작 → SOP 엔진 완성 후 자동 감지로 전환
4. **오탐 신고 → 튜닝 데이터 축적** — 이벤트 DB 스키마에 "확인/오탐" 필드를 미리 넣어둘 것

## 데이터셋 주의사항

- **Roboflow YOLOv8 export의 data.yaml 경로 버그**: 원본이 `train: ../train/images` 처럼
  잘못된 상대경로라 그대로 쓰면 학습 실패. 절대경로 `path:` 키를 추가해 고쳐야 함.
  - Colab: `path: /content/rtauto_sop/datasets/<name>`
  - 로컬: `path: C:/Users/1111/Desktop/rtauto_sop/datasets/<name>`
  - `datasets/`는 gitignore라 이 수정은 커밋에 안 남는다. 다시 받으면 재수정 필요.
- **Hard Hat Workers 데이터셋 재매핑**: 원본 클래스 `head`/`helmet`(또는 `hard hat`)/`person` 중
  `person`을 제거하고 `head`→`no_helmet`, `helmet`→`helmet` 2클래스로 remap해서 사용.
  라벨 `.txt`의 클래스 인덱스를 바꾸고 person 라인은 삭제하는 스크립트로 처리 (Colab 셀).

## 자주 쓰는 명령 (Git Bash, venv 활성 상태)

```bash
# ★ 메인: 감시단원 채널 통합 데모 ('q'로 종료) — 로컬 CPU
python webcam_sop.py                    # 3규칙 전부 (마커 준비됐을 때)
python webcam_sop.py --no-zone           # 마커 없으면 안전구역만 끄고 실행
python webcam_sop.py --crew 3 --zone-hold 5      # 파라미터 조정 (--help 참고)

# Web Push 알림 연동 (터미널 2개 필요)
python generate_vapid_keys.py                     # 최초 1회
uvicorn push_server:app --port 8000               # 터미널 1: 알림 서버 (localhost:8000 접속해 구독)
python webcam_sop.py --push-url http://localhost:8000/notify   # 터미널 2

# 단일 기능 검증용 (통합본 문제 생겼을 때 원인 분리에 유용)
python webcam_helmet.py     # 안전모만
python webcam_person.py     # 인원 수 + 추적만
python webcam_zone.py       # 안전구역만
python debug_aruco.py       # 마커 인식되는지만 (조명/거리/인쇄 문제 진단)
python generate_markers.py  # ArUco 마커 재생성
python predict.py           # test 이미지 일괄 추론
```

데이터셋 다운로드·로컬 학습 스크립트는 없다 — **학습은 전부 Colab에서** (README.md 7절 절차 참고).
Roboflow 다운로드가 로컬에서 다시 필요하면 그 절차를 참고해서 새로 작성.

- **Roboflow API 키는 로컬 어디에도 저장돼 있지 않다.** `~/.roboflow/config.json`, `.env` 모두 없음.
  https://app.roboflow.com/settings/api 에서 Private API Key 확인. 계정 하나에 키 1개, 모든 공개
  데이터셋 다운로드에 공용.

## 컨벤션

- **커밋 메시지: 한국어**. 제목 한 줄 + 필요 시 본문 불릿.
- 커밋 마지막에 `Co-Authored-By: Claude <모델명> <noreply@anthropic.com>` 유지
  (모델명은 그 세션에서 실제 작업한 모델로 — 하네스가 알려주는 값을 쓸 것).
- git 사용자 이메일이 `minha8680@naver.com`으로 설정됨 (GitHub 계정 minha8680, 알림용 이메일은 gmail).
- 커밋/푸시는 **사용자가 요청할 때만**. 사용자가 직접 파일을 작성해보며 진행하는 방식을
  선호하므로, 요청 없이 파일을 미리 만들어두지 말 것. "자동으로 해줘" 요청이 오면 그때 작성.
  (단, 학습 결과 정리처럼 사용자가 "정리해서 커밋해줘"라고 한 작업은 파일 생성까지 진행)
- **비밀정보**: API 키는 코드에 하드코딩 금지, 환경변수로만. `.env`는 gitignore됨.
- **저장소가 public**이므로 알티자동화 내부 자료(구체 견적가, 벤더 제품 링크, 사내 문서 참조,
  기획안 PDF/DOCX)는 커밋/문서에 넣지 않는다. 시스템 구조·기술 스택 같은 기술 설명은 무방.

## 다음 작업 (개발_진행_계획.docx Phase 순)

- [x] helmet_v2 학습 + 로컬 웹캠 테스트 평가
- [x] 인원 수 검출 + ByteTrack 추적
- [x] "N인 1조" + 보호구 미착용 규칙 (`--crew` 등으로 파라미터화)
- [x] 안전구역 침범 — ArUco 마커 기반 **개념 검증**. 마커 재질·인식거리 실측, 부분 가림 대응은 미완
- [x] 위 3규칙을 `webcam_sop.py` 하나로 통합 (= 감시단원 채널 완성)
- [x] Web Push 알림 프로토타입 — 구독 → 위반 시 실제 알림 도달 확인 (`--push-url`)
- [ ] **세정기 SOP 문서 작성 → JSON 스키마 설계** — 코드 작업 아님, 현장 관찰 필요. 이게 있어야
  작업자 채널(항목·순서/급소포인트)과 STEP 소요시간, 규칙 판정 엔진(Phase 4) 착수 가능.
  **현재 최대 병목.** 현장 가기 전 "관찰 체크리스트 + JSON 스키마 초안"을 먼저 만들어두면 효율적
- [ ] (선택, SOP 없이도 가능) 안전구역 PoC 보강 — 마커 3개만 보여도 기하학적으로 4번째 추정
- [ ] (선택) 알림 고도화 — 등급별 차등 발송, 반복 억제 (위 "알림 설계" 섹션 참고. 실제 알림
  채널이 있어야 의미 있으므로 Phase 6에서 같이)
- [ ] (장비 입고 후) RTSP 2채널 수신 + 현장 재튜닝 + GPU 동시 부하 검증
- [ ] (제품화 시점) 검출 프레임워크 라이선스 재검토 (YOLOv8 AGPL → YOLOX/RT-DETR Apache)
