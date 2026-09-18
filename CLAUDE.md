# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code를 위한 안내입니다.

## 프로젝트 개요

**알티자동화(RT Automation)** 의 "작업자 행동인식 기반 SOP 준수 지원 시스템" 시범 과제 중
**AI 모델 학습/검증 파트**의 작업 저장소입니다. 전체 시스템이 아니라, 그 시스템에 들어갈
객체 검출 모델을 준비하는 실험 코드가 여기에 있습니다.

- 작성자: 신민하 (알티자동화)
- 저장소: https://github.com/minha8680/rtauto_sop (**public**)
- 현재 단계: **감시단원 카메라 채널의 3개 판정 항목(N인 1조 / 보호구 착용 / 안전구역 침범)을
  `webcam_sop.py` 하나로 통합 완료** + 관리자 폰 **실제 알림 수신 검증 완료**(FCM + 전용
  Android 앱, 2026-09-15 — Web Push 프로토타입은 폰 미검증으로 별개 유지).
  작업자 카메라 채널(항목·순서, 급소포인트)은 **SOP 문서가 없어 착수 불가**. 다음은 SOP 문서화.
- 기획안 원문(PDF/DOCX)은 사용자 바탕화면에 있고 저장소에는 없다(`*.docx`/`*.pdf` gitignore).
  안전구역 설정 방식은 기획안에 없던 내용이라 "5.7 안전구역 설정 방식" 절을 추가한
  사본을 만들어 둠: `바탕화면/장비_구매_기획안_1안_최종본_안전구역설정방식추가.docx`
- **관리자 휴대폰 알림 앱은 별도 저장소이자 별도 로컬 경로**: 이 저장소(`rtauto_sop`)는
  `Desktop/rtauto_sop`에 있지만, 안드로이드 앱의 실제 작업 폴더는
  **`C:\Users\1111\AndroidStudioProjects\rtauto_sop`** (Android Studio 기본 프로젝트 위치,
  이름은 똑같이 `rtauto_sop`라 헷갈리기 쉬움). 원격 저장소는 아래:
  https://github.com/minha8680/rtauto_sop_android
  (Android/Kotlin, "RT SOP 알림"). FCM data-only 메시지를 받아 알림+진동+알람음+TTS로 재생하는
  수신 전용 앱 — 편차 판정은 여전히 이 저장소(엣지 PC)가 함. 메시지 계약: FCM `data` 페이로드만
  사용(`notification` 금지 — 앱이 백그라운드일 때 커스텀 재생 로직이 안 불림), 필드는
  `kind`("alert"|"resolved", 기본 alert)/`key`(rule:target, 확정↔해제 매칭용)/`title`/`body`/
  `level`(중대·일반·주의, 기본 중대). `kind="resolved"`는 새 알림 없이 같은 key의 알람만 끔
  (기획안 5.6절 해제 조건). 자세한 아키텍처는 그 저장소의 CLAUDE.md 참고.

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
| 안전관리대책 | 헬멧·보안경 착용 | **감시단원** (2~4m) | ✅ `webcam_sop.py` |
| 안전관리대책 | 장갑 착용 | **작업자** (근접 — 감시단원 거리에선 장갑까지 식별 어려움) | ❌ (glove_v1 베이스라인 학습 완료, 2026-09-18. 모델만 확보, 실물 미검증. 작업자 채널 처리기 생기면 그쪽에 통합 — `webcam_sop.py`(감시단원 채널)에는 안 넣음) |
| 위험요인 | 안전구역 침범 | **감시단원** (광역) | ✅ `webcam_sop.py` (PoC) |
| 위험요인 | 위험 자세(사다리 끝단) | **감시단원** (광역) | ❌ |
| 항목·순서 | 단계 순서 위반·누락 | **작업자** (근접) | ❌ SOP 필요 |
| 급소포인트 | 필수 동작 누락·확인 생략 | **작업자** (0.8m 이내) | ❌ SOP 필요 |
| STEP별 작업시간 | 표준시간 초과·과속 | 양 카메라 공통 | ❌ SOP 필요 |

즉 `webcam_sop.py` = 사실상 **"감시단원 채널 처리기"**. 나중에 작업자 채널이 생기면 구조를
이렇게 나눠야 한다(단순히 같은 스크립트를 두 번 돌리는 게 아님 — 채널마다 보는 항목과 모델이 다름):

```
채널 A (작업자캠, 근접)   → 손동작·공구·부품·장갑 검출 → 단계 순서·급소포인트·장갑착용 판정 ─┐
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
- Python 패키지는 `venv/`에 설치됨. **`requirements.txt` 있음** — `pip install --no-cache-dir -r requirements.txt`.
  로컬 추론/프로토타입용이고 학습(Colab)과는 무관. 새 패키지 설치하면 이 파일도 갱신할 것.
  - `opencv-python-headless`가 딸려 들어오면 `cv2.imshow`가 안 된다. headless 제거 후 `opencv-python` 재설치.
  - 콘솔이 **cp949**라 `print()`에 em-dash(—) 같은 비-cp949 문자를 넣으면 `UnicodeEncodeError`가 난다.
    스크립트 출력문엔 일반 하이픈을 쓸 것. 파일 읽기/쓰기는 항상 `encoding="utf-8"` 명시.
  - 한글 파일명을 bash 명령줄로 넘기면 깨진다. 한글 경로가 필요한 작업은 .py 파일로 작성해서 실행할 것.
  - **pip 자체도 cp949 문제를 겪는다**: 한글 주석이 든 `.txt`(requirements.txt 등)에 PEP263
    인코딩 선언(`# -*- coding: utf-8 -*-`) 첫 줄이 없으면 pip가 로케일(cp949)로 읽으려다
    `UnicodeDecodeError`로 깨진다. 한글 주석 넣는 텍스트 파일을 pip가 읽는 경우 항상 첫 줄에
    이 선언을 넣을 것 (requirements.txt에 이미 적용됨, 지우지 말 것).

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
│                        #   person+helmet_v2+glasses_v3+ArUco 구역을 한 루프에서. 4규칙:
│                        #   N인1조(3초) / 헬멧 미착용(10초) / 보안경 미착용(10초) / 안전구역 침범(3초)
│                        #   헬멧·보안경은 완전히 독립 규칙(match_ppe_to_persons 매칭 로직 공유)
│                        #   --crew, --*-hold, --no-zone, --no-glasses, --push-url, --fcm-token,
│                        #   --id-bridge-* 로 파라미터화 (--no-id-bridge로 추적 ID 이어붙이기 끌 수 있음).
│                        #   --source 로 영상 입력 전환(기본 "0"=웹캠, rtsp://...면 자동으로
│                        #   CAP_FFMPEG+저지연 버퍼 적용, video_source.py의 open_video_source
│                        #   공유 — 2026-09-18 추가. 검출 로직은 frame만 보므로 이 인자 말고는
│                        #   안 바뀜, 실장비 검증은 아직).
│                        #   위반 확정/해제는 on_violation_confirmed/resolved 공통 지점을
│                        #   거쳐 events.jsonl 기록 + clips/ 클립 저장 + (설정 시) Web Push/FCM 발송
│                        #   — 새 규칙 추가돼도 이 두 함수만 호출하면 전부 자동으로 따라옴
├── view_events.py       # events.jsonl을 사람이 읽기 좋게(확정↔해제 짝짓고 지속시간까지) 출력
├── push_server.py       # Web Push 알림 프로토타입 서버(FastAPI). 구독 페이지 + /notify
├── generate_vapid_keys.py  # Web Push용 VAPID 키 생성 (최초 1회)
├── send_test_alert.py   # rtauto_sop_android 앱으로 FCM data-only 테스트 발송 (엣지 PC 역할 대신)
│                        #   service-account.json(gitignore) + DEVICE_TOKEN 환경변수 필요
├── rtsp_test.py         # 바디캠 RTSP 연결/지연/재연결만 검증 (검출 모델 없음, 2026-09-18 추가)
│                        #   장비 입고 직후 가장 먼저 돌려볼 것 — 연결 자체가 불안정하면
│                        #   검출 품질을 논할 단계가 아니므로. python rtsp_test.py rtsp://...
├── video_source.py      # 웹캠/RTSP 여는 공통 함수(open_video_source) — webcam_sop.py와
│                        #   rtsp_test.py가 공유(2026-09-18, 중복 코드 정리). 검출 로직과 무관
├── generate_markers.py  # ArUco 마커 4장(TL/TR/BR/BL) 생성 → markers/
├── markers/             # 생성된 마커 PNG (프린트해서 구역 네 모서리에 배치)
├── trackers/bytetrack_person.yaml  # 저FPS(CPU)용 ByteTrack 튜닝 설정
├── requirements.txt      # 로컬 실행 환경. 첫 줄 인코딩 선언 지우지 말 것(위 cp949 메모 참고)
│
│   ── 아래는 단계별 검증용으로 남겨둔 단일 기능 스크립트 (통합본은 webcam_sop.py) ──
├── webcam_helmet.py     # 안전모 착용/미착용만
├── webcam_glasses.py    # 보안경 착용/미착용만 (glasses_v3, webcam_sop.py에 통합 완료·이건 단독 검증용)
├── webcam_glove.py      # 장갑 착용/미착용만 (glove_v1, 베이스라인·실물 미검증·통합 전, 단독 검증용)
├── webcam_person.py     # 인원 수+추적+2인1조 규칙만
├── webcam_zone.py       # 안전구역 침범만 (MarkerMemory 원본 구현)
├── debug_aruco.py       # 마커 인식 자체만 진단 (코드 vs 조명/거리 문제 분리용)
├── predict.py           # 학습 가중치로 test 이미지 일괄 추론
│                        # main.py 자리는 비워둠 — 2채널 통합 파이프라인이 생기면 그게 진입점
├── docs/
│   ├── helmet_v1/       # 착용 위주 데이터셋 baseline 결과 (실패 사례)
│   ├── helmet_v2/       # 착용/미착용 2클래스 결과 (성공) + webcam_test.md
│   ├── glasses_v1/      # 보안경 착용/미착용 2클래스 결과 (지표는 성공, 실물 검증 실패 — 아래 참고)
│   ├── glasses_v2/      # glasses_v1의 실물 인식 실패는 고쳤지만 일반 안경 오탐 발견 — 아래 v3 참고
│   ├── glasses_v3/      # spec(일반 안경)을 배경이 아닌 no_goggles로 재매핑 — 현재 사용 중
│   ├── glove_v1/        # 장갑 착용/미착용 베이스라인 (mAP50 0.933) — 실물 미검증, 작업자 채널용
│   └── bodycam_test_guide.md  # 포팩트 LIVE ST20 입고 후 테스트 절차 (특정 모델에 안 묶인 첫 플랫 문서)
├── models/              # .gitignore(*.pt) — helmet_v1/v2_best.pt, glasses_v1/v2/v3_best.pt,
│                        #                     glove_v1_best.pt (전부 로컬 전용)
├── datasets/, runs/, venv/          # .gitignore
├── yolov8n.pt                        # 사전학습 가중치 (*.pt로 제외)
├── vapid_private_key.pem            # .gitignore(*.pem) — Web Push 서명 키, 비공개
├── vapid_public_key.txt             # .gitignore — 구독용 공개 키
├── push_subscriptions.json          # .gitignore — 구독자 엔드포인트(개인 기기 토큰)
├── events.jsonl                     # .gitignore — 위반 확정/해제/클립저장 이력 (런타임 로그)
├── clips/                           # .gitignore — 경보 구간 클립(mp4), 위반 확정 시 자동 생성
├── 개발_진행_일지.docx               # .gitignore(*.docx) — 날짜순 개발 기록 (로컬 전용)
├── README.md
└── CLAUDE.md
```

`.gitignore`: `venv/`, `*.pt`, `datasets/`, `runs/`, `.env`, `*.pem`, `vapid_public_key.txt`,
`push_subscriptions.json`, `service-account.json`, `events.jsonl`, `clips/`, `*.docx`, `*.pdf`,
`.idea/`, `.vscode/`

## 학습한 모델

| 모델 | 데이터셋 | 클래스 | 결과 | 파일 |
|---|---|---|---|---|
| helmet_v1 | Roboflow `hard-hat-detection-ws2wk` v1 (668장) | hard hat / no hard hat / not hard hat | mAP50 0.41. 착용 recall 0.91, **미착용 0.00~0.33 (실패)** | `models/helmet_v1_best.pt` |
| **helmet_v2** | Roboflow `joseph-nelson/hard-hat-workers` (~7,000장) | helmet / no_helmet (person 제외) | **mAP50 0.96. 착용 recall 0.97, 미착용 0.95 (성공)** | `models/helmet_v2_best.pt` |
| glasses_v1 | Roboflow PPE Combined Model에서 Goggles/NO-Goggles만 필터링 (8,280 인스턴스, 1:1 균형) | glasses / no_glasses | mAP50 0.97, 지표는 성공했지만 **실물 풀페이스 고글 인식은 완전 실패**(2026-09-17, 실물+프린트 둘 다 0건) — 데이터셋이 "Goggles"란 이름과 달리 안경형 위주였던 것으로 추정 | `models/glasses_v1_best.pt` |
| glasses_v2 | Roboflow `seafty_goggles`에서 spec(일반 안경) **드롭**, goggles/no_goggles만 사용 (5,936:4,122) | glasses / no_glasses | mAP50 0.97, glasses_v1의 실물 고글 인식 실패는 해결했지만 **1m 거리 일반 안경을 0.6 confidence로 고글 오탐**(2026-09-18 발견) — spec을 배경으로 버려서 대조 신호가 없었던 게 원인 | `models/glasses_v2_best.pt` |
| **glasses_v3** | glasses_v2와 동일 데이터셋, spec을 배경 대신 **no_goggles로 재매핑**(goggles 5,936:no_goggles 6,304) | glasses / no_glasses | **mAP50 0.97, 착용 recall 0.98, 미착용 0.96 — v2보다 전 지표 개선.** glasses_v2_best.pt에서 warm start, 30 epoch만에 도달 | `models/glasses_v3_best.pt` |
| **glove_v1** | Roboflow `safety-gloves-xbnf8` v5 (10,459장, Gloves 4,669:NO-Gloves 6,135, 원본부터 2클래스라 재매핑 불필요) | Gloves / NO-Gloves | **mAP50 0.933, 착용 recall 0.930, 미착용 0.903 (베이스라인, 2026-09-18).** yolov8n.pt부터 50epoch. helmet·glasses보다 낮지만 준수한 수준 — 손 형태가 더 가변적이라는 게 원인으로 추정. **실물 미검증** — 작업자 채널 처리기 생기기 전까지 통합 안 함(카메라 2채널 표 참고) | `models/glove_v1_best.pt` |

- **핵심 교훈**: helmet_v1과 v2는 학습 설정 동일, **데이터셋만 교체**. 미착용 학습 표본이
  16~64개 → 1,000개 이상으로 늘자 미착용 recall 0.00 → 0.95. "학습량이 아니라 데이터 문제".
- 자세한 지표는 `docs/helmet_v1/metrics.md`, `docs/helmet_v2/metrics.md`, `docs/glasses_v1/metrics.md`,
  `docs/glasses_v2/metrics.md`, `docs/glasses_v3/metrics.md`, `docs/glove_v1/metrics.md`,
  웹캠 테스트 평가는 `docs/helmet_v2/webcam_test.md`.
- **glasses_v1 → v2 교훈(2026-09-17)**: 학습 지표(mAP50 0.97)가 좋아도 **데이터셋 클래스명만
  믿고 실제 이미지 스타일을 확인 안 하면 실물에서 완전히 실패할 수 있다** — helmet_v1(표본
  수 부족)과는 또 다른 종류의 실패. 새 데이터셋을 고를 때는 (1) Roboflow API로 정확한
  인스턴스 수 조회 (2) 후보들이 이름만 다른 동일 원본인지 확인 (3) 대표 이미지로 실제 스타일
  확인, 이 세 단계를 거칠 것 — `docs/glasses_v2/metrics.md`에 상세 절차 기록.
- **glasses_v2 → v3 교훈(2026-09-18)**: 학습 데이터셋에 이미 존재하는 대조 클래스(`spec`)를
  "우리 판정엔 필요 없다"고 배경으로 버리면, 모델이 그 대상과 목표 클래스를 구분할 근거
  자체를 잃는다 — 오히려 **의미상 같은 결론으로 묶이는 클래스는 배경이 아니라 목표
  클래스로 합쳐서 명시적 대조군으로 쓸 것**(여기선 "안전고글 미착용"이라는 같은 결론이라
  no_goggles로 합침). 또한 이미 학습된 가중치가 있으면 yolov8n.pt부터 새로 학습하지 말고
  **그 가중치에서 warm start**하면 훨씬 적은 epoch로 같거나 더 나은 결과에 도달할 수 있다
  (v2: yolov8n.pt부터 50epoch, v3: glasses_v2_best.pt에서 30epoch로 전 지표 개선).

### 데이터셋 출처·라이선스 (2026-09-11 확인, public 저장소라 반드시 지킬 것)

| 모델 | 데이터셋 출처 | 라이선스 | 의무사항 |
|---|---|---|---|
| helmet_v1 | [Hard hat detection](https://universe.roboflow.com/adamson-university-nrlyj/hard-hat-detection-ws2wk) (Adamson University, Roboflow Universe, v1, 668장) | **CC BY 4.0** | 출처 표기 필요 (원저작자 표기 없이 그대로 배포·재공유 금지) |
| helmet_v2 | [Hard Hat Workers](https://universe.roboflow.com/joseph-nelson/hard-hat-workers) (Roboflow 재공개, 원출처 Northeastern University - China, Harvard Dataverse doi:10.7910/DVN/7CBGOS, ~7,000장) | **Public Domain (CC0 1.0)** | 없음 — 출처 표기 의무는 없으나 관례상 계속 표기 |
| glasses_v1 | [Personal Protective Equipment - Combined Model](https://universe.roboflow.com/roboflow-universe-projects/personal-protective-equipment-combined-model) (Roboflow Universe, 44,002장 중 Goggles/NO-Goggles만 필터링) | **CC BY 4.0** | 출처 표기 필요 (실물 검증 실패로 v2로 대체, 출처 표기는 계속 유지) |
| glasses_v2 | [seafty_goggles](https://universe.roboflow.com/abduls-okhnp/seafty_goggles) (Roboflow Universe, v9, 9,149장 중 goggles/no_goggles만 사용, spec 제외) | **CC BY 4.0** | 출처 표기 필요 (일반 안경 오탐으로 v3로 대체, 출처 표기는 계속 유지) |
| glasses_v3 | 위와 동일 데이터셋(seafty_goggles v9), spec을 no_goggles로 재매핑해서 사용 | **CC BY 4.0** | 출처 표기 필요 |
| glove_v1 | [safety-gloves](https://universe.roboflow.com/roboflow-universe-projects/safety-gloves-xbnf8) (Roboflow Universe, v5, 10,459장) | **CC BY 4.0** | 출처 표기 필요 |

- 데이터셋 모두 상업적 이용 제한은 없음(CC BY 4.0도 상업적 사용 허용, 조건은 출처 표기뿐).
- **학습된 가중치(`models/helmet_v1_best.pt`, `helmet_v2_best.pt`, `glasses_v1/v2/v3_best.pt`,
  `glove_v1_best.pt`) 자체는 `*.pt`로 gitignore돼 저장소엔 없음** — 그래도 데이터셋 출처는 공개 코드/문서
  (`docs/helmet_v1/`, `docs/helmet_v2/`, `docs/glasses_v1/`, `docs/glasses_v2/`,
  `docs/glasses_v3/`, `docs/glove_v1/`, 이 표)에 항상 남겨둘 것.

## 프로젝트 완성도 (현실 체크)

**완료**: **감시단원 카메라 채널의 판정 항목 4개 전부**(N인 1조 / 헬멧 착용 / 보안경 착용 /
안전구역 침범)를 `webcam_sop.py` 하나로 통합. 안전구역은 알고리즘 **개념 검증(PoC)** 수준.
실제로 있는 것:

- helmet_v2, glasses_v3 검출 모델 (재사용 가능한 핵심 자산 — 둘 다 `webcam_sop.py` 통합
  완료. glasses는 v1(실물 풀페이스형 고글 인식 실패) → v2(일반 안경을 고글로 오탐) → v3
  (spec을 no_goggles로 재매핑, 전 지표 개선)로 두 번 교체(2026-09-17~18) — 상세는
  `docs/glasses_v2/metrics.md`, `docs/glasses_v3/metrics.md`)
- glove_v1 검출 모델 (mAP50 0.933, 2026-09-18 완료 — 상세는 `docs/glove_v1/metrics.md`).
  **실물 미검증, `webcam_sop.py`에는 통합 안 함** — 작업자 채널(아직 없음) 담당 항목이라
  모델 자산으로만 확보해 둔 상태
- Colab 학습 파이프라인 (glasses_v1/v2/v3, glove_v1로 재사용 검증됨 — 클래스만 다른
  데이터셋 재활용에 효과적. v2부터는 세션 끊김 대비 Drive 체크포인트 저장 + 자동 이어학습
  방식도 도입)
- person 검출 + ByteTrack 추적 + 공간 매칭(`match_ppe_to_persons`, helmet·glasses 공유) +
  `SustainedLatch` 규칙 패턴 (지속시간 확정/해제, 재사용되는 핵심 로직)
- ArUco 마커로 "카메라가 움직여도 구역을 다시 찾는" 방식 — 웹캠에서 동작 검증됨
- Web Push 알림 프로토타입 — 구독 → 위반 확정 시 실제 브라우저 알림까지 경로 검증됨.
  반복(flapping) 억제는 클립 저장에만 적용(2026-09-16, 알림은 매번 발송 — 아래 알림 설계 참고)
- 이벤트 로그(`events.jsonl` + `view_events.py`) — 알림 설정과 무관하게 위반 확정/해제
  전부 기록. `on_violation_confirmed/resolved` 공통 지점 덕에 새 규칙 추가해도 재사용됨
- 경보 구간 클립(`clips/`) — 위반 확정 시 최근 10초 mp4 자동 저장, 이벤트 로그에 경로도 기록
- 실험 결과·한계 문서

**아직 없는 것 (= 시스템 본체)**:
- **작업자 카메라 채널 전체** (항목·순서, 급소포인트) — SOP 문서가 없어 착수 불가
- SOP JSON + 규칙 판정 엔진, STEP 소요시간 — 마찬가지로 SOP 문서가 선행 조건
- 2채널 동시 수신·통합 구조 (지금은 단일 카메라 전제)
- 편차 등급별 재발송·ACK 스케줄러, 작업 세션(근무시간) 게이팅 (알림 반복 억제·등급 표시는 완료)
- 음성 경로(STT/TTS/헤드셋), 엣지 PC 통합, heartbeat 로직, 위험 자세 검출
- 실제 웹캠 구동 중 위반 발생 → FCM 자동 알림의 전체 경로 실측 (함수 연결은 완료, 실측은 다음 단계)
- **판정 유효 거리 게이트** — 사람 박스가 너무 작으면(= 너무 멀면) 보호구 규칙을 판정 보류로
  돌리는 로직. 지금은 크기 제한이 없어 거리와 무관하게 검출되면 그대로 알림까지 간다.
  기획안 그림 2의 거리별 구간 표는 설계 의도일 뿐 미구현 — 아래 "다음 작업"의 해당 항목 참고

**바디캠이 와도 "꽂으면 시스템이 돈다"가 아니다.** `cv2.VideoCapture(0)` → `VideoCapture("rtsp://…")`
한 줄 변경 자체는 쉽지만, RTSP는 버퍼링·지연 관리, 끊김 재연결, 2채널 동시 수신, 3fps 다운샘플링,
SoftAP 무선망 구성이 별도로 필요하다 (며칠짜리). 바디캠 입고의 의미는 **helmet_v2 모델을 실제
현장 거리·화각(2~4m, 안전모 22~35px)에서 검증 시작**할 수 있게 되는 것이다.

**안전구역 PoC도 마찬가지로 "완성"이 아니다.** 마커 3개(1개 가림)까지는 평행사변형 근사로
버티지만(2026-09-11 추가), 2개 이하로 줄면 여전히 판정 보류다. 실전 적용 전 필요한 것:
방수·내구성 있는 마커 재질, 4~10m 거리에서 인식되는 크기 실측, 부착 위치 결정. 추정 근사는
카메라가 정면에 가까울 때만 잘 맞고 각도가 심하면 오차가 커진다는 점도 실측으로 확인 필요.
`webcam_sop.py`/`webcam_zone.py` 최상단 docstring에 한계 정리돼 있음.

"helmet 검출 = 착용"이 아니라는 점도 중요 (`webcam_test.md` 한계 1). `webcam_sop.py`에서
person/helmet 박스의 공간 관계(박스 안에 중심점 포함)로 이미 해결함 — 새로 만들 때 이 로직
재사용할 것.

**버그 수정(2026-09-16, 사용자 발견)**: `PersonState`가 "미확인"(각도·거리로 helmet/no_helmet
어느 쪽도 못 잡은 프레임)을 "착용"과 똑같이(해제 조건 False) 취급해서, 헬멧이 잠깐 화면
밖으로 나가기만 해도 실제로는 계속 미착용인 위반이 `--helmet-clear` 다 채우지 않고 조기에
풀려버렸음. `ZoneState`(마커 안 보이면 판정 동결)와 다르게 헬멧 쪽만 이 원칙이 안 지켜지고
있었던 것 — `votes`가 비면(최근 `SMOOTH_SEC` 안에 어떤 판정도 없으면) latch를 아예 갱신하지
않고 동결하도록 수정. 단위 테스트로 "미확인이 5초 넘게 지속돼도 위반이 안 풀리고, 진짜
착용이 지속돼야만 풀리는지" 검증.

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

### 관리자 폰 실제 알림 수신 — FCM 경로로 검증 완료 (2026-09-15)

위 Web Push(브라우저 기반) 프로토타입과는 **별개의 두 번째 알림 경로**로, 전용 Android 앱
([rtauto_sop_android](https://github.com/minha8680/rtauto_sop_android))을 만들어 FCM(Firebase
Cloud Messaging)으로 전환 — **실제 휴대폰에 알림이 뜨는 것까지 확인됨**. Web Push가 막혔던
HTTPS/MDM 문제를 우회한 셈(네이티브 앱은 브라우저 Push API 제약을 안 받음).

- 이 저장소(엣지 PC 역할)에서 `send_test_alert.py`로 FCM data-only 메시지 발송 →
  앱의 `AlertFcmService`가 수신 → 알림+진동+알람음+TTS 재생까지 앱 쪽에서 처리
- 필요한 것: Firebase 서비스 계정 키(`service-account.json`, gitignore) + 앱이 발급한
  기기 토큰(`DEVICE_TOKEN` 환경변수) — 둘 다 이 저장소엔 없고 로컬/환경변수로만 존재
- **`webcam_sop.py`에 연결 완료(2026-09-15)** — `--fcm-token`(또는 `DEVICE_TOKEN` 환경변수)을
  주면 4규칙(N인1조/헬멧/보안경/안전구역) 위반이 실제로 확정될 때마다 `on_violation_confirmed`가
  `send_fcm()`을 호출해 자동으로 폰에 알림이 간다. `--push-url`과 동시에 켤 수 있고(둘 다 발송),
  규칙별 등급(`FCM_LEVEL_BY_RULE`: crew/zone=중대, helmet/glasses=주의)도 같이 보내 앱의 등급 배지에 반영됨.
  RepeatThrottle 게이트도 Web Push와 동일하게 적용(반복 위반 시 억제).
  **2026-09-16 실제 웹캠으로 검증 완료** — 그 과정에서 PersonState "미확인" 처리 버그도 발견·수정(아래)
- **위반 해제 시 폰 알람 자동 종료(2026-09-15 완료, 앱 쪽도 같이 수정)** — 기획안 5.6절
  "해제 조건"(사람의 확인이 아니라 동일 검출 경로 재확인으로만 해제)을 반영. 확정 메시지에
  `kind="alert"`, 해제 메시지에 `kind="resolved"`를 같은 `key`(`fcm_key(rule, target)`,
  예 `"helmet:7"`)와 함께 실어 보내고, 앱(`rtauto_sop_android`)이 그 key로 "지금 울리는
  경보와 같은 건인지" 맞춰봐서 자동으로 알람만 끈다(새 알림 없이 조용히). 해제 신호는
  RepeatThrottle과 무관하게 항상 발송 — 확정이 스로틀에 막혀 폰까지 안 갔으면 앱에서 매칭될
  게 없어 조용히 무시되고, 실제로 갔으면 해제도 반드시 도착해 알람이 안 꺼진 채 안 남게 함.
  단위 테스트로 confirmed/resolved의 key가 항상 일치하는지 검증. 앱 쪽 변경은
  `rtauto_sop_android`의 `feature/fcm-auto-resolve` 브랜치, Kotlin 컴파일 확인 완료 —
  실제 폰 설치·동작 확인은 다음 단계
- `push_server.py`(Web Push)는 초기 프로토타입으로 남겨두되, 실제 알림 경로는 이쪽(FCM+전용
  앱)으로 굳어지는 중 — 최종적으로 하나로 정리할지는 추후 결정
- **iOS 지원 판단 보류(2026-09-15)**: `rtauto_sop_android`는 **Android 전용**. 지금 관리자는
  Android지만 나중에 iOS 쓰는 관리자가 생길 가능성이 있어, iOS용 앱을 따로 만들지는 보류.
  그래서 **`push_server.py`(Web Push, Android/iOS 공통)를 지우지 않고 iOS 대안 경로로 유지**
  하기로 함 — iOS 관리자가 실제로 생기면 그때 Web Push 쪽을 마저 완성(휴대폰 실 수신 검증 등)
  하거나 iOS FCM 앱을 새로 만들지 결정

### 알림 설계 — 나중에 반영할 논의 결과 (오탐 피로 방지)

관리자에게 알림이 너무 자주 가면 신뢰를 잃는다(alarm fatigue). `push_server.py`(실제 알림
채널)는 이미 있다:
1. **등급별 차등 발송** — 기획안 그림 4 목업에 이미 중대/일반/주의 3등급이 있음. 중대(2인1조)만
   30초 재발송, 주의(보호구)는 1회, 일반(표준시간 초과)은 이벤트 목록에만 기록. **미구현, 규모
   큼** — `push_server.py`에 백그라운드 재발송 스케줄러, 확인(ACK) 엔드포인트, 알림에 "확인"
   액션 버튼(서비스워커), 이벤트 이력 저장소까지 새로 필요.
2. **반복(flapping) 억제 — 클립 저장에만 적용(2026-09-11 구현, 2026-09-16 정책 변경)** —
   `webcam_sop.py`의 `RepeatThrottle` 클래스(메서드명도 `should_notify`→`should_save_clip`로
   변경, 실제로 게이트하는 게 클립뿐이라). 원래는 알림까지 같이 억제했지만, 실사용해보니
   재감지된 실제 위반은 매번 알려야 안전하다는 피드백으로 **알림(Push/FCM)은 이제 반복
   여부와 무관하게 항상 보낸다** — 알림 피로는 앱 쪽 안전장치(아래 관리자 폰 섹션의 "자동
   해제 N건" 배지, "다른 활성 위반" 펼치기)로 완화하는 쪽으로 방향을 바꿨다. 클립 저장은
   여전히 억제한다 — 해제 후 `--repeat-cooldown-min`(기본 5분) 안에 같은 유형(규칙+사람 ID)이
   다시 걸리면 클립 생략, `--repeat-threshold`(기본 3)회 도달 시 클립 재개 + 알림 문구에
   "N회 반복" 표시. 규칙별(crew/helmet/zone) + 사람 ID별로 독립적으로 카운트(키 충돌 없음,
   단위 테스트로 검증).
3. **작업 세션 게이팅** — 점심·교대 시간엔 규칙 평가 자체를 끔. **미구현, 2026-09-11 보류 판단**:
   "카메라 물리적으로 끄기 비추천"은 **무인 엣지 PC 운영 시점** 얘기(끄고 켜는 걸 사람이 잊으면
   기록 공백·오작동 구분 불가). 지금은 개발자가 터미널에서 직접 실행/종료하는 프로토타입 단계라
   Ctrl+C로 충분 — 자동 스케줄링은 무인 운영 착수 시점에 만들 것.
4. **오탐 신고 → 튜닝 데이터 축적** — 이벤트 DB 스키마에 "확인/오탐" 필드를 미리 넣어둘 것. 미구현

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
python webcam_sop.py                    # 4규칙 전부 (마커 준비됐을 때)
python webcam_sop.py --no-zone           # 마커 없으면 안전구역만 끄고 실행
python webcam_sop.py --no-glasses        # glasses_v3 없이 헬멧만 판정
python webcam_sop.py --crew 3 --zone-hold 5      # 파라미터 조정 (--help 참고)

# Web Push 알림 연동 (터미널 2개 필요)
python generate_vapid_keys.py                     # 최초 1회
uvicorn push_server:app --port 8000               # 터미널 1: 알림 서버 (localhost:8000 접속해 구독)
python webcam_sop.py --push-url http://localhost:8000/notify   # 터미널 2

# 실제 관리자 폰 앱(rtauto_sop_android)으로 FCM 테스트 발송 — 엣지 PC 없이 이 PC에서 대신 발송
export DEVICE_TOKEN="앱 홈 화면에서 복사한 토큰"
python send_test_alert.py     # service-account.json 필요 (Firebase 콘솔에서 발급, gitignore)

# webcam_sop.py에서 실제 위반 검출 시 자동으로 폰에 FCM 알림 (DEVICE_TOKEN 위와 동일하게 설정 후)
python webcam_sop.py --fcm-token "$DEVICE_TOKEN"                       # FCM만
python webcam_sop.py --push-url http://localhost:8000/notify --fcm-token "$DEVICE_TOKEN"   # 둘 다

# 위반 이력 확인 (webcam_sop.py 실행 중/후 아무 때나, --push-url 없어도 기록됨)
python view_events.py                # 전체
python view_events.py --rule zone --today

# 클립 없이/저장 길이 조정하고 싶으면
python webcam_sop.py --no-clip
python webcam_sop.py --clip-sec 5

# 단일 기능 검증용 (통합본 문제 생겼을 때 원인 분리에 유용)
python webcam_helmet.py     # 안전모만
python webcam_glasses.py    # 보안경만 (glasses_v3)
python webcam_glove.py      # 장갑만 (glove_v1, 베이스라인·실물 미검증)
python webcam_person.py     # 인원 수 + 추적만
python webcam_zone.py       # 안전구역만
python debug_aruco.py       # 마커 인식되는지만 (조명/거리/인쇄 문제 진단)
python generate_markers.py  # ArUco 마커 재생성
python predict.py           # test 이미지 일괄 추론

# 바디캠 입고 직후 최우선으로 돌려볼 것 — RTSP 연결 자체만 검증 (검출 모델 없음)
python rtsp_test.py rtsp://<카메라IP>:<포트>/<경로>
python rtsp_test.py rtsp://<카메라IP>/live --no-display   # 화면 없이 콘솔 로그만 (장시간용)
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
  선호하므로, 요청 없이 파일을 미리 만들어두지 말 것. 자동으로 처리해달라는 요청이 오면 그때 작성.
  (단, 학습 결과 정리처럼 정리해서 커밋해달라고 한 작업은 파일 생성까지 진행)
- **비밀정보**: API 키는 코드에 하드코딩 금지, 환경변수로만. `.env`는 gitignore됨.
- **저장소가 public**이므로 알티자동화 내부 자료(구체 견적가, 벤더 제품 링크, 사내 문서 참조,
  기획안 PDF/DOCX)는 커밋/문서에 넣지 않는다. 시스템 구조·기술 스택 같은 기술 설명은 무방.

## 다음 작업 (상세 이력은 `개발_진행_일지.docx` 참고, 로컬 전용·날짜순)

- [x] helmet_v2 학습 + 로컬 웹캠 테스트 평가
- [x] 인원 수 검출 + ByteTrack 추적
- [x] "N인 1조" + 보호구 미착용 규칙 (`--crew` 등으로 파라미터화)
- [x] 안전구역 침범 — ArUco 마커 기반 **개념 검증**. 마커 재질·인식거리 실측은 미완(현장 실측 필요)
- [x] 위 3규칙을 `webcam_sop.py` 하나로 통합 (= 감시단원 채널 완성)
- [x] Web Push 알림 프로토타입 — 구독 → 위반 시 실제 알림 도달 확인 (`--push-url`)
- [x] `requirements.txt` 작성
- [x] 안전구역 PoC 보강 — 마커 3개(1개 가림)일 때 평행사변형 근사로 4번째 추정
  (`webcam_sop.py`/`webcam_zone.py` 둘 다 적용, `--no-zone-estimate`/`ALLOW_ZONE_ESTIMATE`로 끌 수 있음).
  마커 2개 이하로 줄면 여전히 판정 보류
- [x] 세정기 현장 관찰 체크리스트 작성 (`세정기_작업_현장_관찰_체크리스트.docx`, 로컬 전용)
- [ ] **세정기 현장 관찰 → SOP 문서 작성 → JSON 스키마 설계** — 코드 작업 아님, 현장 방문 필요.
  체크리스트는 준비됐으니 다음은 실제 현장 관찰. 이게 있어야 작업자 채널(항목·순서/급소포인트)과
  STEP 소요시간, 규칙 판정 엔진 착수 가능. **현재 최대 병목.** 스키마는 실측 데이터
  나오기 전에 미리 설계하지 않기로 함(추측성 설계 지양, 2026-09-11 판단)
- [x] 알림 반복 억제 (`RepeatThrottle`) — `--repeat-cooldown-min`/`--repeat-threshold`
- [x] 이벤트 로그 (`events.jsonl`, `view_events.py`) — `on_violation_confirmed/resolved`
  공통 지점으로 리팩터링, 알림 설정과 무관하게 항상 기록
- [x] 경보 구간 클립 저장 (`FrameBuffer`, `clips/`) — 그림4 "10초 클립 자동 첨부" 대응.
  `--clip-sec`/`--no-clip`. 저장은 동기 처리라 그동안 프레임 밀림 — 실전엔 스레드 분리 필요
- [x] **버그 수정(2026-09-11, 사용자 지적)**: 클립 저장이 `RepeatThrottle`을 안 거쳐서 반복
  위반(구역 들락날락 등)마다 매번 클립을 새로 쓰는 "녹화 폭탄" 상태였음. `push_url` 없으면
  스로틀 자체가 멈추는 문제도 겹쳐 있었음. `on_violation_confirmed`를 "로그는 항상, 클립·알림은
  스로틀 판단 하나로 공통 게이트"로 재구성 — `mark_resolved`/`should_notify`를 push_url과
  무관하게 항상 호출하도록 고침. 단위 테스트로 flapping 시 clip_saved 로그가 급감하는지,
  디스크에 실제로 적게 남는지 검증
- [ ] 위험 자세 검출 — 표1 위험요인의 나머지 하나(안전구역은 완료). **2026-09-11 재검토**: "위험
  자세"를 SOP 기준(이 작업 단계에선 이 자세가 정상/위험)으로 판정하려면 SOP 문서가 선행돼야
  해서 지금은 착수 불가 — 세정기 현장 관찰과 같은 병목. 대신 SOP와 무관한 **범용 낙상/이상자세
  감지**(COCO pose keypoint로 몸이 갑자기 수평이 되는 등)로 스코프를 좁히면 착수는 가능하다는
  방향만 논의함, 아직 미착수. 착수 시 "SOP 특정 판정 아님, 범용 proxy" 라고 문서에 명시할 것
- [ ] 음성 경로 PoC — 마이크→VAD→faster-whisper STT→키워드 의도 분류→TTS 응답. **현재 로컬
  환경에 마이크·스피커가 없어 진행 불가(2026-09-11 확인)** — 하드웨어 확보 후 재검토. SOP 내용
  없이도 뼈대는 검증 가능(SOP 조회 부분만 가짜 응답으로)할 계획이었음
- [x] **보안경(safety glasses) 착용 검출 모델 학습 (2026-09-14 완료)** — Roboflow PPE Combined
  Model(44,002장, CC BY 4.0)에서 Goggles/NO-Goggles만 라벨 필터링(유료 "Modify Classes" 대신
  스크립트로 처리) → Colab 50 epoch 학습. **mAP50 0.97, 착용 recall 0.98, 미착용 0.95 —
  helmet과 달리 첫 시도부터 성공**(학습 전 클래스 균형 4,188:4,092 확인해둔 덕). 결과:
  `models/glasses_v1_best.pt`, `docs/glasses_v1/metrics.md`. `webcam_glasses.py`로 로컬 웹캠
  단독 테스트 가능 — 아직 `webcam_sop.py` 통합 전(다음 단계). **이후 2026-09-17 실물 검증에서
  완전 실패가 발견돼 glasses_v2로 교체됨 — 아래 해당 항목 참고**
- [x] **관리자 폰 실제 알림 수신 검증 (2026-09-15 완료)** — 전용 Android 앱
  ([rtauto_sop_android](https://github.com/minha8680/rtauto_sop_android))을 만들어 FCM으로
  전환, `send_test_alert.py`로 발송 → **실제 휴대폰 알림 도달 확인**. Web Push가 막혔던
  HTTPS/MDM 문제를 네이티브 앱으로 우회
- [x] **FCM을 webcam_sop.py에 연결 (2026-09-15 완료)** — `--fcm-token`(`DEVICE_TOKEN` 환경변수도
  가능)으로 3규칙 위반 확정 시 실제 폰 알림 자동 발송. 규칙별 등급(중대/주의)도 같이 전달,
  RepeatThrottle 게이트 동일 적용. **2026-09-16 실제 웹캠으로 최종 확인 완료** —
  그 과정에서 PersonState "미확인" 처리 버그를 발견해 같이 수정함(아래 항목)
- [x] **위반 해제 시 폰 알람 자동 종료 (2026-09-15 완료, 2026-09-16 실기기 검증+병합)** —
  기획안 5.6절 "해제 조건"(ACK이 아니라 재감지로만 해제) 반영. `on_violation_resolved`도
  FCM(`kind="resolved"`)을 보내 앱이 같은 `key`의 알람을 자동으로 멈추게 함. 앱 쪽
  (`C:\Users\1111\AndroidStudioProjects\rtauto_sop`)도 같이 수정, 실기기로 확인 후
  `feature/fcm-auto-resolve` → `main` PR 머지 완료. 같은 브랜치에 알림 탭 시 경보상세
  직행, 다크모드 매 실행 시 라이트 리셋도 같이 들어감
- [x] **PersonState "미확인" 처리 버그 수정 (2026-09-16, 사용자 발견)** — 헬멧이 잠깐
  화면 밖으로 나가 판정 불가 상태("미확인")가 되면 "착용"과 똑같이 취급해 해제 타이머가
  진행되던 문제. `ZoneState`(마커 안 보이면 판정 동결)와 다르게 헬멧만 이 원칙이 안
  지켜지고 있었음 — `votes`가 비면 latch 자체를 갱신하지 않도록 수정, 단위 테스트로 검증
- [x] **추적 ID 이어붙이기 — PersonIdentityMemory 추가 (2026-09-16, 실험적)** — 사람이 잠깐
  화면을 벗어나거나 빠르게 움직이면 ByteTrack이 새 추적 ID를 매기는데, 위반 판정이 이
  ID를 키로 저장하다 보니 ID가 바뀔 때마다 실제로는 안 풀렸는데 "해제"로 보고되고 새
  ID로 타이머가 처음부터 다시 도는 문제(사용자 발견 — 실제 현장에서는 같은 사람의 추적
  ID가 계속 바뀌면 안 된다는 지적). `MarkerMemory`와 같은 철학으로 해결: 방금(`--id-bridge-gap-sec`,
  기본 2초) 사라진 사람의 마지막 위치(`--id-bridge-dist-px`, 기본 120px) 근처에 새 ID가
  나타나면 같은 사람(canonical id)으로 이어붙임. 완벽한 재식별(ReID)이 아니라 짧은 이탈만
  버티는 가벼운 다리라 **실험적 기능으로 표시** — 오작동(엉뚱한 두 사람을 하나로 합침 등)
  시 `--no-id-bridge`로 끄고 예전처럼 raw ID를 바로 쓸 수 있음. 단위 테스트로 (1)짧은
  이탈 이어붙임 (2)먼 거리는 새 사람 취급 (3)오래 사라지면 새 사람 취급 (4)동시에 존재하는
  두 사람이 한 canonical로 합쳐지지 않음 4가지 검증. **실제 웹캠 검증은 다음 단계**
- [x] **알림은 반복 억제 대상에서 제외 + 여러 위반 동시 처리 (2026-09-16, 실제 웹캠+폰 테스트로
  발견)** — 2인1조 위반이 열려있는 도중 헬멧 미착용까지 확정되는 실제 상황에서 두 가지 문제
  발견: (1) 헬멧이 자동 해제된 뒤 다시 미착용이 재확정돼도 RepeatThrottle이 억제해서 폰이
  다시 안 울림 → **알림(Push/FCM)을 반복 억제 대상에서 뺌**, 클립 저장만 계속 억제
  (`RepeatThrottle.should_notify`→`should_save_clip`로 이름도 정리). (2) 헬멧이 자동 해제되고
  대기 중이던 2인1조 위반이 다음 경보로 카드에 뜨는데 경고음·TTS가 안 울림 → 앱 쪽에
  `AlertPlayer.promoteNextIfAny()` 추가, 알람을 끌 때(수동 확인·자동 해제 둘 다) 아직 확인
  안 된 다른 위반이 있으면 그걸 위해 알람을 다시 켬(`rtauto_sop_android`, 같은 세션에서
  Kotlin 컴파일 확인). 알림 피로는 이제 앱 쪽 안전장치(자동 해제 N건 배지, 다른 활성 위반
  펼치기, 알림 그룹 요약)로 해결 — 발송 억제로 해결하지 않는 쪽으로 방향 전환
- [x] **버그 수정(2026-09-17, 사용자 발견)**: `--helmet-clear`/`--zone-clear`를 몇 초로
  줘도 헬멧을 다시 쓰자마자 바로 "자동해제"가 뜨는 문제. 원인은 `SustainedLatch`가 아니라
  `helmet_violation_ids`/`zone_violation_ids`가 매 프레임 `person_items`(이번 프레임에
  검출된 사람)만 순회해 다시 채워지던 구조 — 헬멧을 쓰려고 손을 머리로 올리다 person 검출/
  추적이 한 프레임이라도 끊기면, 헬멧 판정과 무관하게 그 pid가 그냥 목록에서 빠져 즉시
  "해제"로 오판됐음(`--*-clear` 하이스터리시스 자체를 건너뜀). `carry_forward_violations()`
  추가 — 이번 프레임에 재검출 안 된 pid라도 마지막 `latch.latched`가 True면 위반 목록에
  이어서 포함시키고, 실제 해제는 재검출 후 `pstate.update()`가 `clear_sec`만큼 "착용"을
  확인해야만 일어나게 함. 계속 안 보이면 기존 30초 정리 로직으로 그때 비로소 해제됨. 단위
  테스트로 (1)순간적으로 안 보여도 위반 유지 (2)clear_sec 다 안 채우면 유지 (3)clear_sec
  채우면 정상 해제 (4)person_states에서 정리된 pid는 대상에서 빠짐 4가지 검증
- [ ] **사람 부재 처리 설계 (2026-09-17, 논의만 하고 보류 — 정책 질문은 현장 도입 여부
  정해지면 재검토)**: `carry_forward_violations()`가 "순간적으로 안 보임"만 다루는데,
  실제로는 성격이 다른 두 상황이 더 있음이 논의됨 — (1) 작업자 한 명이 화장실 등으로
  몇십 초~몇 분 자리를 비움(개별 부재), (2) 감시 카메라 자체가 다른 곳을 보거나 가려져서
  `person_items`가 통째로 0명이 됨(시스템적 부재, 특정 인물이 아니라 전체가 안 보임 — 몇
  명이 한꺼번에 사라졌는지로 (1)/(2) 구분 가능). 설계 방향: "모름" 상태를 경과 시간에 따라
  3단계로(즉시 무시 → "자리비움"으로 표시하되 알림은 끔 → 오래 지속되면 추적 자체 포기)
  나누고, (2)는 개별 위반 판정이 아니라 "카메라 시야 이상" 같은 별도 종류의 신호(heartbeat
  개념, 아래 "아직 없는 것" 목록의 heartbeat 로직과 연결됨)로 분리해서 다뤄야 한다는 데까지
  논의함. **구현 보류, 아래 정책적 질문에 대한 답이 있어야 착수 가능**:
  1. 개인 자리비움을 "정상"으로 봐줄 유예시간(몇 분?)
  2. 자리비움에서 복귀했을 때 이전 위반 판정을 이어갈지, 모른다로 보고 새로 판정할지
  3. 카메라 시야 이상을 관리자 폰에도 FCM으로 알릴지, 화면 배너로만 표시할지
  세 질문 모두 지금 급하게 정하지 않고 현장 도입 여부가 정해진 뒤 결정하기로 함 — 사용자 판단
- [x] **glasses_v1을 webcam_sop.py에 통합 (2026-09-17 완료)** — helmet과 완전히 독립된
  네 번째 규칙으로 추가(`--glasses-hold`/`--glasses-clear`/`--no-glasses`). 매칭 로직을
  `match_helmet_to_persons`→`match_ppe_to_persons(person_items, boxes, labels, positive_label)`로
  일반화해 helmet·glasses가 공유(라벨 딕셔너리와 "착용"에 해당하는 라벨만 다르게 넘김).
  `PersonState`도 헬멧 전용이 아니라 그대로 재사용(hold/clear 각각 별도 인자로 분리).
  `combined_color`/`draw_overlay`에 보안경 상태·위반 태그·배너 추가. `FCM_LEVEL_BY_RULE`에
  `glasses: "주의"`(helmet과 동급) 추가. 단위 테스트로 (1)같은 매칭 함수가 helmet/glasses
  라벨 조합 모두에서 정확히 동작 (2)안 겹치는 사람은 None (3)FCM 등급 (4)`--no-glasses`/
  `--glasses-hold`/`--glasses-clear` 파싱 검증 — 실제 웹캠 통합 동작 확인은 다음 단계.
  **실물 검증에서 한계 발견**: 지금 쓰는 실물 보안고글(풀페이스 단일렌즈형)과 그 사진 프린트
  둘 다 인식 실패 — `docs/glasses_v1/metrics.md` "다음 단계" 3번 참고, 데이터셋 보강 필요
  가능성. `--no-glasses`로 끄면 예전처럼 헬멧+구역만으로 계속 쓸 수 있음
- [ ] **glasses_v1 실패를 계기로 대체 데이터셋 조사 + glove_v1 베이스라인 학습 착수
  (2026-09-17)** — Roboflow에서 "Goggles"란 클래스명만 보고 실패를 반복하지 않으려고, 이번엔
  (1) 여러 후보의 클래스 인스턴스 수를 Roboflow API로 직접 조회(페이지 스크래핑 대신 —
  `https://api.roboflow.com/{workspace}/{project}?api_key=...`가 `classes` 필드로 정확한
  숫자를 줌), (2) 후보들 상당수가 이름만 다르고 사실상 같은 원본 데이터(인스턴스 수 거의
  일치)라는 걸 발견, (3) 프로젝트 아이콘 썸네일(`source.roboflow.com/.../thumb.jpg`, 이건
  직접 접근 가능)로 대표 이미지 스타일을 실제로 확인하는 절차를 정립함 — 앞으로 새 데이터셋
  고를 때 이 세 단계(인스턴스 수 API 조회 → 동일 원본 여부 확인 → 대표 이미지로 스타일 확인)를
  거칠 것. glasses_v2 후보: `abduls-okhnp/seafty_goggles`(v9, goggles 5,936/no_goggles
  4,122/spec 2,182, CC BY 4.0) — 사용자가 브라우저로 풀페이스 고글 혼재 확인함, `spec`(일반
  안경)은 제외하고 재매핑해서 학습(Colab, Drive 저장+10에포크 체크포인트+세션 끊김 시
  자동 이어학습 구조 — 아래 별도 항목에 완료 기록). glove_v1 베이스라인:
  `roboflow-universe-projects/safety-gloves-xbnf8`(v5, 10,459장, Gloves 4,669/NO-Gloves
  6,135, CC BY 4.0, 이미 2클래스라 재매핑 불필요) — 대표 이미지가 실제 CCTV 스타일 산업현장
  영상이라 도메인 격차 위험이 적어 보임. **장갑은 카메라 담당이 감시단원이 아니라 작업자
  채널**이라는 걸 사용자가 확인해줌(위 "카메라 2채널" 표 참고) — 베이스라인 학습 자체는
  카메라 채널과 무관하게 지금 진행 가능하지만, 나중에 실제 통합할 때는 `webcam_sop.py`
  (감시단원 채널)가 아니라 작업자 채널 처리기(아직 없음, SOP 선행 필요)에 붙여야 함.
  glove_v1 학습 자체는 2026-09-18 완료 — 결과는 아래 별도 항목 참고
- [x] **glasses_v2 학습 완료 + 실물 재검증 성공, webcam_sop.py 전환 완료 (2026-09-17)** —
  seafty_goggles(spec 제외) 50 epoch 학습. **mAP50 0.974, 착용 recall 0.973, 미착용 recall
  0.935** — glasses_v1과 비슷한 수준의 지표. Colab 세션 끊김 대비 `save_period=10` +
  Google Drive 직접 저장(`project=`) + `resume=True` 자동 이어학습 구조를 이번에 처음
  적용(중간에 실제로 런타임이 한 번 리셋됐고, 재실행 안내로 정상 복구됨 — 셀 1~3 재실행 필요성
  재확인). **핵심 검증**: glasses_v1이 conf=0.01까지 낮춰도 0건이었던 실물 보안고글 사진을
  glasses_v2로 재테스트 → `goggles 0.410`으로 정상 검출, 박스 위치도 육안 확인. `models/
  glasses_v2_best.pt`, `docs/glasses_v2/metrics.md`로 정리. `webcam_sop.py`의
  `GLASSES_MODEL_PATH`, `webcam_glasses.py`의 `MODEL_PATH` 둘 다 v2로 전환 완료 — **실제
  웹캠으로 돌려보는 최종 확인은 다음 단계**
- [x] **glasses_v2 실제 웹캠 검증에서 새 문제 발견 → glasses_v3로 재교체 (2026-09-18)** —
  1m 거리 일반 안경을 confidence 0.6으로 "고글"이라고 오탐(사용자 실사용 중 발견). 원인은
  glasses_v2 학습 시 원본 데이터셋의 3번째 클래스 `spec`(일반 안경)을 배경으로 드롭해서,
  모델이 "이건 고글이 아니다"라는 대조 신호를 일반 안경에 대해 못 받았던 것 — 원거리
  저해상도 문제가 아니라(1m는 오히려 근접) 모델이 진짜로 못 배운 것으로 확인(confidence가
  낮지 않고 0.6으로 높았음). **해결**: `spec`을 배경이 아니라 `no_goggles`로 재매핑해서
  재학습 — "일반 안경 착용"과 "미착용" 둘 다 SOP상 "안전고글 미착용"이라는 같은 결론이라
  의미상으로도 맞는 매핑. `glasses_v2_best.pt`에서 warm start, 30 epoch만에 **mAP50 0.974
  (동일), 착용 recall 0.980(v2 0.973), 미착용 recall 0.961(v2 0.935) — 양쪽 다 개선**.
  기존 실물 풀페이스 고글 사진도 재검증(confidence 0.410→0.781로 상승, 회귀 없음). `models/
  glasses_v3_best.pt`, `docs/glasses_v3/metrics.md`로 정리. `webcam_sop.py`/`webcam_glasses.py`
  둘 다 v3로 전환, 기존 단위 테스트 5종 재검증 통과. **1m 거리 일반 안경 오탐이 실제로
  해결됐는지는 캡처 이미지가 없어 문서화 못함 — 실제 웹캠 재확인이 다음 단계**
- [x] **glove_v1 베이스라인 학습 완료, 결과 확보 (2026-09-18)** — 사용자가 로컬 다운로드
  폴더에 받아둔 Colab 학습 산출물(best.pt·results.csv/png·confusion_matrix.png)을 확인해
  정리. `safety-gloves-xbnf8`(v5, 10,459장) 50 epoch 학습으로 **mAP50 0.933, 착용 recall
  0.930, 미착용 recall 0.903** — helmet_v2(0.96)·glasses_v3(0.974)보다는 낮지만 준수한
  수준(손 형태가 헬멧·고글보다 가변적인 게 원인으로 추정). 학습 곡선에 과적합 징후 없음.
  같은 세션에 로컬 다운로드 폴더에 섞여 있던 파일 3세트(무표시/`(1)`/`(2)`) 중 앞 두 개는
  파일 크기가 이미 정리된 `models/glasses_v2_best.pt`·`glasses_v3_best.pt`와 정확히
  일치함을 확인해 걸러내고, confusion matrix의 클래스명(Gloves/NO-Gloves)으로 나머지
  하나가 진짜 glove_v1 결과임을 확인 후 진행 — 파일 착각 방지 절차로 기록해둘 만함.
  `models/glove_v1_best.pt`, `docs/glove_v1/metrics.md`로 정리, 단독 검증용
  `webcam_glove.py` 추가. **실물 미검증** — glasses_v1이 mAP50 0.97에도 실물에서 완전히
  실패했던 전례가 있어 이 수치만으로 현장 적용 가능 여부를 판단하지 않음. 카메라 담당이
  작업자 채널(아직 없음)이라 `webcam_sop.py`(감시단원 채널)에는 통합하지 않음
- [ ] **보안경 2m+ 원거리 오탐 — 여러 시도 실패, 원복하고 하드웨어 재검증으로 미룸
  (2026-09-18)**: glasses_v3로도 2~4m 거리에서 일반 안경을 고글로 오인식하는 문제가
  실제 웹캠 검증에서 확인됨. 원인을 좁혀보려고 순서대로 시도함 — **모두 근본 해결은
  실패했고 부작용만 남겨서 전부 되돌림**(`webcam_sop.py`/`webcam_glasses.py`는 glasses_v3
  모델 경로 전환만 남기고 커밋 `8b4e095` 상태로 리셋):
  1. 추론 `imgsz`를 640→1024로 상향 — 50cm는 고쳐졌지만 1m 이상은 그대로
  2. 보안경 판정을 프레임 전체 대신 **사람 전신 박스로 crop**해서 확대(`detect_glasses_per_person`
     신설) — 전신 박스를 자르면 크롭 안에서도 얼굴 비율이 원본과 거의 같아서(몸 전체의
     1/6~1/7) 실질적 확대 효과가 거의 없었음(실측: 모델 입력 기준 얼굴이 77px→106px 정도
     차이). 2~4m 오탐 그대로
  3. **웹캠 캡처 해상도**가 `cv2.VideoCapture(0)` 기본값(640x480)으로 찍히고 있던 걸 발견해
     1920x1080으로 명시 설정 — 같은 거리에서 얼굴 픽셀 높이가 57px→131px로 실측 증가(2.3배,
     해상도 배율과 일치)했지만, **그래도 2~4m 오탐은 그대로였고 오히려 헬멧 판정까지
     불안정해짐**(캡처 해상도 변경이 프레임을 공유하는 헬멧 모델에도 영향을 준 것으로 추정)
  4. crop 대상을 전신이 아니라 **머리 영역만**(전신 박스 위쪽 22%, `GLASSES_HEAD_FRACTION`)으로
     좁혀서 진짜 디지털 줌 효과를 내도록 재설계 — 여전히 2~4m 오탐 지속, 게다가 착용/미착용
     판정이 프레임마다 심하게 flip-flop, 헬멧 오탐도 안 없어짐

  **결론**: 임계값·crop·해상도 같은 파이프라인 조정으로는 안 풀리는 문제로 보임 — 웹캠
  자체의 화질/압축/오토포커스 특성과 학습 데이터(seafty_goggles)의 촬영 조건이 근본적으로
  다른 도메인 격차일 가능성이 높음. **지금 쓰는 노트북 웹캠은 기획안상 실제 배치 카메라
  (포팩트 LIVE ST20, 2K 촬영)와 다른 장비라 여기서 더 튜닝해도 실제 하드웨어에서 재현될지
  알 수 없음** — 바디캠 입고 후 그 카메라로 재검증하기 전까지는 더 파고들지 않기로 함.
  **당장 2m+ 신뢰도가 필요하면 `--no-glasses`로 보안경 판정을 끄고 헬멧+구역만 쓸 것.**
- [ ] **거리(박스 크기) 게이트 없음 — 기획안 그림 2와 코드가 어긋나 있다 (2026-09-18 사용자
  질문으로 발견, 기록만 하고 보류)**: "FCM 알림이 거리 무관하게 검출만 되면 발송되는
  구조냐"는 질문을 확인해보니 **그렇다**. `webcam_sop.py`에 최소 박스 크기나 판정 유효 거리
  임계값이 아예 없다(`PERSON_CONF=0.4`만 통과하면 크기와 무관하게 규칙 평가에 들어가고,
  미착용이 `--*-hold`만큼 지속되면 `on_violation_confirmed` → `send_fcm`이 무조건 발송.
  RepeatThrottle은 클립만 게이트하므로 알림은 안 막는다).
  - **문서 불일치**: 기획안 그림 2에 "4~6m 보안경 판정 불가 / 6~10m 보호구 판정 불가 /
    10m 초과 판정 보류 구간"이라고 써놨지만 그건 **설계 의도일 뿐 미구현**이다. 기획안이
    코드보다 앞서 있는 상태 — 현장 도입 전에 맞춰야 한다.
  - **규칙별로 원거리 실패 방향이 다르다**: 헬멧·보안경은 멀면 보호구 박스가 아예 안 잡혀
    "미확인"이 되고 `votes`가 비어 latch가 동결되므로(2026-09-16 수정분) 오알림보다 **미탐**
    쪽으로 기운다. 반면 **인원 수(crew)는 "검출 안 되면 위반"이라 멀어서 사람을 놓치면
    2인 미달로 중대 등급 오알림이 간다** — 아래 "사람 부재 처리 설계" 항목(카메라가 다른
    곳을 보거나 가려져 0명이 되는 경우)과 같은 뿌리의 문제다. 안전구역은 마커가 안 보이면
    판정 보류로 동결되니 이 문제에서 자유롭다.
  - **구현 방향**: 사람 박스 높이(또는 어깨 폭) 하한을 임계값으로 두고 그보다 작으면 보호구
    규칙을 "판정 보류"로 돌린다(마커 안 보일 때 `ZoneState`를 동결하는 것과 같은 철학).
    기획안 그림 2의 구간 표가 사실상 그 게이트의 명세이므로 **픽셀 기준값만 실측으로 정하면
    바로 넣을 수 있다** — 그 실측은 바디캠 입고 후 항목이라 지금은 착수하지 않는다.
    crew 쪽은 게이트만으로 안 풀리고 부재/시야 이상 판정과 같이 설계해야 한다.
- [ ] (선택) 알림 등급별 차등 발송 — 위 "알림 설계" 섹션 참고. 서버 쪽 스케줄러·ACK까지
  필요해 규모가 큼, 지금 급하지 않음
- [ ] **바디캠 구매 리스크 논의 + 1대 우선 구매로 결정 (2026-09-18)**: 포팩트 LIVE ST20를
  사면 실제로 제대로 작동할지 불안하다는 사용자 질문에 코드·문서 재점검으로 답함 — `webcam_sop.py` 포함 전 스크립트가
  아직 `cv2.VideoCapture(0)`(웹캠)만 쓰고 **RTSP 코드가 저장소에 한 줄도 없음**을 확인.
  확실한 위험 요소로 (1) 보안경 2~4m 오탐이 이 카메라에서도 재현될지 미지수(2026-09-18
  4차 시도 실패 항목과 동일 뿌리) (2) **130° 광각이 2K 해상도 이점을 상쇄** — 1도당 픽셀
  밀도가 일반 카메라(65° 근사) 대비 약 절반(19.7 vs 39.4 px/도)이라 원거리 오탐이 오히려
  악화될 수 있음 (3) WiFi(SoftAP) 송출 배터리 지속시간이 기획안 표4에 "미공개"로만 적혀
  있음(LTE 기준 5.5시간만 공표) (4) 금속 설비 인근에서 SoftAP 반경이 공표치(15m)의 절반
  이하로 줄 수 있음(기획안에 이미 명시) (5) 마커 인식 거리(4~10m)도 데스크 PoC까지만 검증.
  **결정**: 2대 동시 구매 대신 **1대만 먼저 구매**해 감시단원 채널 리스크(원거리 판정)를
  전부 검증한 뒤 2대째를 결정하기로 함 — 작업자 채널(근접)은 위험이 적어 우선순위 낮음.
  검증 순서(리스크·비용 큰 순): ① RTSP 연결 자체 → ② 보안경 2~4m 오탐 재현 여부(최우선,
  결과에 따라 fine-tuning 또는 유효거리 2m 제한 결정) → ③ 헬멧 2~4m 판정 → ④ WiFi 송출
  배터리 지속시간 실측 → ⑤ SoftAP 반경 실측 → ⑥ 마커 인식 거리 실측. ①②가 사실상
  "2대째를 살 가치가 있는가"를 가르는 게이트. **상세 절차는 `docs/bodycam_test_guide.md`로
  문서화함(아래 별도 항목).**
- [x] **`rtsp_test.py` 추가 — RTSP 연결/지연/재연결만 검증하는 최소 스크립트 (2026-09-18)**:
  위 검증 순서 ①을 장비 입고 즉시 돌릴 수 있게 미리 준비. 검출 모델은 전혀 안 씀(연결
  안정성과 검출 품질을 분리해서 진단하려는 목적 — `debug_aruco.py`가 마커 인식을 조명/거리
  문제와 코드 문제로 분리하는 것과 같은 철학). `cv2.CAP_FFMPEG` 명시 + `CAP_PROP_BUFFERSIZE=1`로
  지연 누적 방지, 끊기면 최대 5회 자동 재연결, 5초마다 실측 FPS·재연결·끊김 횟수를 콘솔에
  출력. `CAP_PROP_OPEN/READ_TIMEOUT_MSEC`도 걸어뒀지만 **FFmpeg 빌드에 따라 정확히 안
  지켜질 수 있음을 로컬 테스트로 확인**(더미 주소로 8초 타임아웃 설정해도 더 오래 멈춤) —
  알려진 한계로 스크립트 주석에 남겨둠. 실제 카메라로 검증은 다음 단계(RTSP 주소는 카메라
  입고 후 매뉴얼/앱에서 확인 필요, 지금은 알 수 없음)
- [x] **`webcam_sop.py`에 `--source` 인자 추가 (2026-09-18)**: 실장비가 오면 헬멧·보안경
  인식이 되게 하려고 코드를 전부 고쳐야 하는지 묻는 사용자 질문에, `_run()`이 `cap.read()`로 나온
  `frame`(이미지)만 받아서 동작하고 그 출처(웹캠/RTSP)는 전혀 모르는 구조임을 코드로 확인해
  답함 — 실제로 바뀌어야 할 건 `cv2.VideoCapture(0)` 한 줄뿐이었음. `open_video_source(source)`
  헬퍼를 추가해 `--source`가 정수면 웹캠(기존과 동일), `rtsp://`/`rtsps://`로 시작하면
  `rtsp_test.py`와 동일한 `CAP_FFMPEG`+`CAP_PROP_BUFFERSIZE=1`+타임아웃 설정을 자동 적용하도록
  분기. 기본값이 `"0"`이라 `--source` 없이 실행하면 이전과 완전히 동일하게 동작함(회귀 없음,
  더미 RTSP 주소로 분기 로직 자체는 검증함). **검출 로직·매칭·규칙 엔진·FCM은 한 글자도 안
  바뀜.** 여전히 없는 것: 2채널(작업자+감시단원) 동시 처리 구조(지금도 `cap` 1개만 받음),
  RTSP 재연결 로직(webcam_sop.py 자체엔 없음, `rtsp_test.py`에만 있음 — 필요하면 나중에
  옮겨 붙일 것), 실제 장비로 인식 정확도가 맞는지(임계값·픽셀 크기 가정)는 완전히 별개 문제로
  미검증 상태
- [x] **`video_source.py`로 공통 모듈 분리 (2026-09-18, 사용자 지적)** — webcam_sop.py에
  다 몰아넣는 것보다 파일을 따로 만드는 게 낫지 않냐는 지적에 동의해 리팩터링. 직전 항목에서
  `webcam_sop.py`와 `rtsp_test.py`가 사실상 같은 코드(`CAP_FFMPEG`+저지연 버퍼+타임아웃 설정)를
  각자 파일에 복사해서 갖고 있던 상태였음 — 이대로 두면 나중에 한쪽만 고치고 잊어버리는
  설정 드리프트 위험이 있었음. `open_video_source()`를 `video_source.py`로 옮기고 두 파일
  모두 `from video_source import open_video_source`로 가져다 쓰게 정리, 중복 제거 확인(`grep`으로
  `open_stream`/`RTSP_*` 상수 잔재 없음 검증). 부수효과(print)는 공유 함수에서 빼고 호출하는
  쪽(`main()`)에서 하도록 분리 — 공통 유틸은 순수 함수로 유지. 나중에 2채널 동시 처리 구조로
  갈 때도 채널마다 이 함수를 한 번씩 불러 쓰면 되도록 설계해둠
- [x] **`docs/bodycam_test_guide.md` 작성 — 장비 입고 후 테스트 절차 문서화 (2026-09-18)**:
  실장비가 왔을 때 테스트하는 방법도 설명해달라는 사용자 요청으로, 위에서 논의만 하고
  넘어갔던 검증 순서(①RTSP 연결 ②보안경 2~4m 오탐 ③헬멧 2~4m ④배터리 지속시간 ⑤SoftAP
  반경 ⑥마커 인식 거리)를 실행 가능한 절차로 구체화. 각 단계마다 실제 명령어
  (`rtsp_test.py`, `webcam_sop.py --source`, `debug_aruco.py`), 통과 기준, 실패 시 대응을
  명시. `docs/` 하위 첫 "모델 전용이 아닌" 플랫 문서 — 기존엔 `docs/<model>/`처럼 모델별
  폴더만 있었는데, 이건 하드웨어 검증 절차라 특정 모델에 안 묶여서 새 위치로 둠. 결과는
  아직 없음(실측 전) — 실측 후 이 문서 하단에 결과 절을 채울 것
- [ ] (장비 입고 후) RTSP 2채널 수신 + 현장 재튜닝 + GPU 동시 부하 검증
- [ ] (제품화 시점) 검출 프레임워크 라이선스 재검토 (YOLOv8 AGPL → YOLOX/RT-DETR Apache)
