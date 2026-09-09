# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code를 위한 안내입니다.

## 프로젝트 개요

**알티자동화(RT Automation)** 의 "작업자 행동인식 기반 SOP 준수 지원 시스템" 시범 과제 중
**AI 모델 학습/검증 파트**의 작업 저장소입니다. 전체 시스템이 아니라, 그 시스템에 들어갈
객체 검출 모델을 준비하는 실험 코드가 여기에 있습니다.

- 작성자: 신민하 (알티자동화)
- 저장소: https://github.com/minha8680/rtauto_sop (**public**)
- 현재 단계: 헬멧(안전모) 착용 검출 모델 PoC — 공개 데이터셋으로 학습이 도는지부터 확인

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

- **OS**: Windows 10, 주 셸은 **Git Bash (MINGW64)**. PowerShell 아님 — 가상환경 활성화 등
  명령을 안내할 때 Git Bash 문법으로 준다.
- **가상환경 활성화**: `source venv/Scripts/activate` (활성 시 프롬프트에 `(venv)`)
- **GPU 없음**: `torch.cuda.is_available()` → `False`. 학습은 **CPU only**.
  안내 시 `device="cpu"`, 낮은 `imgsz`(416), 작은 `batch`(4), 적은 `epochs`를 전제로.
- Python 패키지는 `venv/`에 설치됨. `requirements.txt`는 아직 없음(만들면 유용).

## 저장소 구조

```
rtauto_sop/
├── main.py              # 웹캠 + YOLO 실시간 추론 테스트 (yolov8n 사전학습)
├── download_dataset.py  # Roboflow에서 헬멧 데이터셋 다운로드 (API 키는 환경변수)
├── train.py             # 헬멧 검출 학습 스크립트 (현재 스모크 테스트 설정)
├── datasets/            # .gitignore 대상 — 커밋 안 됨
│   └── helmet_public/   # Roboflow "hard-hat-detection-ws2wk" v1, yolov8 포맷
│       ├── train/ valid/ test/  (각 images/ + labels/)
│       └── data.yaml
├── runs/                # .gitignore 대상 — 학습 결과물
├── venv/                # .gitignore 대상
├── yolov8n.pt           # 사전학습 가중치 (.gitignore의 *.pt로 제외)
├── README.md
└── CLAUDE.md
```

### 데이터셋 (datasets/helmet_public)

- 출처: Roboflow `adamson-university-nrlyj / hard-hat-detection-ws2wk` version 1, `yolov8` 포맷
- 클래스 **3개** (`nc: 3`): `hard hat`, `no hard hat`, `not hard hat`
- 이미지 수: train 468 / valid 133 / test 67
- **data.yaml 경로 주의**: Roboflow 원본은 `train: ../train/images` 처럼 잘못된 상대경로라
  학습이 실패한다. 절대경로 `path:` 키를 추가해 고쳐둔 상태:
  ```yaml
  path: C:/Users/1111/Desktop/rtauto_sop/datasets/helmet_public
  train: train/images
  val: valid/images
  test: test/images
  ```
  `datasets/`는 gitignore라 이 수정은 커밋에 안 남는다. **데이터셋을 다시 받으면 재수정 필요** —
  장기적으로 `download_dataset.py`에 data.yaml 자동 패치 코드를 넣는 게 좋다.

## 자주 쓰는 명령 (Git Bash, venv 활성 상태)

```bash
# 데이터셋 다운로드 (키는 이 터미널에서만 유효)
export ROBOFLOW_API_KEY="<본인 키>"
python download_dataset.py

# 학습
python train.py

# 웹캠 추론 테스트 ('q'로 종료)
python main.py

# GPU 확인
python -c "import torch; print(torch.cuda.is_available())"
```

### train.py 관련 메모

- `project="runs"` 로 두면 ultralytics 기본값과 겹쳐 `runs/detect/runs/helmet_smoke` 처럼
  경로가 중첩된다. `name=`만 주고 `project=`는 빼거나 `project="runs/detect"`로 두는 게 깔끔.
- 스모크 테스트(epochs=3, imgsz=416) 통과 후 본 학습은 epochs 30~50, imgsz 640으로.
  CPU라 1 epoch 실측 시간을 먼저 재고 총 시간을 산정할 것.

## 컨벤션

- **커밋 메시지: 한국어**. 제목 한 줄 + 필요 시 본문 불릿.
- 커밋 마지막에 `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` 유지.
- git 사용자 이메일이 `minha8680@naver.com`으로 설정됨 (GitHub 계정 minha8680).
- 커밋/푸시는 **사용자가 요청할 때만**. 사용자가 직접 파일을 작성해보며 진행하는 방식을
  선호하므로, 요청 없이 파일을 미리 만들어두지 말 것. "자동으로 해줘" 요청이 오면 그때 작성.
- **비밀정보**: API 키는 코드에 하드코딩 금지, 환경변수로만. `.env`는 gitignore됨.
- **저장소가 public**이므로 알티자동화 내부 자료(구체 견적가, 벤더 제품 링크, 사내 문서 참조)는
  커밋/문서에 넣지 않는다. 시스템 구조·기술 스택 같은 기술 설명은 무방.
```
