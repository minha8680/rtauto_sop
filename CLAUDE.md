# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code를 위한 안내입니다.

## 프로젝트 개요

**알티자동화(RT Automation)** 의 "작업자 행동인식 기반 SOP 준수 지원 시스템" 시범 과제 중
**AI 모델 학습/검증 파트**의 작업 저장소입니다. 전체 시스템이 아니라, 그 시스템에 들어갈
객체 검출 모델을 준비하는 실험 코드가 여기에 있습니다.

- 작성자: 신민하 (알티자동화)
- 저장소: https://github.com/minha8680/rtauto_sop (**public**)
- 현재 단계: **안전모 착용/미착용 검출 완료(helmet_v2)** → 다음은 인원 수 검출(person) + 추적(ByteTrack)
- 전체 로드맵: `개발_진행_계획.docx` (gitignore, 로컬 전용) — Phase 1~8

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
  설치돼 있는 주요 패키지: `ultralytics`, `torch(cpu)`, `opencv-python`(headless 아님), `roboflow`, `python-docx`.
  - `opencv-python-headless`가 딸려 들어오면 `cv2.imshow`가 안 된다. headless 제거 후 `opencv-python` 재설치.

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
├── main.py              # 웹캠 실시간 추론 테스트. MODEL_PATH=models/helmet_v2_best.pt, CONF 조정 가능
├── predict.py           # 학습 가중치로 test 이미지 일괄 추론
├── download_dataset.py  # Roboflow 데이터셋 다운로드 (API 키는 환경변수 ROBOFLOW_API_KEY)
├── train.py             # 로컬 학습 스크립트 (CPU 스모크 테스트용, 실사용 아님)
├── docs/
│   ├── helmet_v1/       # 착용 위주 데이터셋 baseline 결과 (실패 사례)
│   └── helmet_v2/       # 착용/미착용 2클래스 결과 (성공)
├── models/              # .gitignore(*.pt) — helmet_v1_best.pt, helmet_v2_best.pt (로컬 전용)
├── datasets/            # .gitignore — 커밋 안 됨
├── runs/                # .gitignore — 로컬 학습 결과물
├── venv/                # .gitignore
├── yolov8n.pt           # 사전학습 가중치 (*.pt로 제외)
├── 개발_진행_계획.docx    # .gitignore(*.docx) — 전체 로드맵
├── README.md
└── CLAUDE.md
```

`.gitignore`: `venv/`, `*.pt`, `datasets/`, `runs/`, `.env`, `*.docx`, `*.pdf`, `.idea/`, `.vscode/`

## 학습한 모델

| 모델 | 데이터셋 | 클래스 | 결과 | 파일 |
|---|---|---|---|---|
| helmet_v1 | Roboflow `hard-hat-detection-ws2wk` v1 (668장) | hard hat / no hard hat / not hard hat | mAP50 0.41. 착용 recall 0.91, **미착용 0.00~0.33 (실패)** | `models/helmet_v1_best.pt` |
| **helmet_v2** | Roboflow `joseph-nelson/hard-hat-workers` (~7,000장) | helmet / no_helmet (person 제외) | **mAP50 0.96. 착용 recall 0.97, 미착용 0.95 (성공)** | `models/helmet_v2_best.pt` |

- **핵심 교훈**: helmet_v1과 v2는 학습 설정 동일, **데이터셋만 교체**. 미착용 학습 표본이
  16~64개 → 1,000개 이상으로 늘자 미착용 recall 0.00 → 0.95. "학습량이 아니라 데이터 문제".
- 자세한 지표는 `docs/helmet_v1/metrics.md`, `docs/helmet_v2/metrics.md`.

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
# 웹캠 추론 테스트 ('q'로 종료) — 로컬 CPU
python main.py

# test 이미지 일괄 추론
python predict.py

# 로컬 데이터셋 다운로드 (실사용은 Colab에서)
export ROBOFLOW_API_KEY="<본인 키>"
python download_dataset.py
```

- **Roboflow API 키는 로컬 어디에도 저장돼 있지 않다.** `~/.roboflow/config.json`, `.env` 모두 없음.
  https://app.roboflow.com/settings/api 에서 Private API Key 확인. 계정 하나에 키 1개, 모든 공개
  데이터셋 다운로드에 공용.

## 컨벤션

- **커밋 메시지: 한국어**. 제목 한 줄 + 필요 시 본문 불릿.
- 커밋 마지막에 `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` 유지.
- git 사용자 이메일이 `minha8680@naver.com`으로 설정됨 (GitHub 계정 minha8680, 알림용 이메일은 gmail).
- 커밋/푸시는 **사용자가 요청할 때만**. 사용자가 직접 파일을 작성해보며 진행하는 방식을
  선호하므로, 요청 없이 파일을 미리 만들어두지 말 것. "자동으로 해줘" 요청이 오면 그때 작성.
  (단, 학습 결과 정리처럼 사용자가 "정리해서 커밋해줘"라고 한 작업은 파일 생성까지 진행)
- **비밀정보**: API 키는 코드에 하드코딩 금지, 환경변수로만. `.env`는 gitignore됨.
- **저장소가 public**이므로 알티자동화 내부 자료(구체 견적가, 벤더 제품 링크, 사내 문서 참조,
  기획안 PDF/DOCX)는 커밋/문서에 넣지 않는다. 시스템 구조·기술 스택 같은 기술 설명은 무방.

## 다음 작업 (개발_진행_계획.docx Phase 순)

1. helmet_v2 로컬 웹캠 테스트 + conf 임계값 튜닝  ← 진행 중
2. 인원 수 검출 (person, COCO 사전학습 → 학습 불필요) + ByteTrack 추적
3. 검출→추적→규칙 1개(2인 1조) 미니 통합 데모
4. (병행) 세정기 SOP 문서 → JSON 스키마 설계
