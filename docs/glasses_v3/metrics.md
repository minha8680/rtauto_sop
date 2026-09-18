# glasses_v3 — 일반 안경 오탐 수정 (spec을 배경이 아닌 no_goggles로 재매핑)

glasses_v2가 실물 풀페이스 고글은 정상 인식했지만(mAP50 0.974), **1m 거리의 일반 안경을
0.6 confidence로 "고글"로 오탐**하는 문제가 발견돼(2026-09-18, 실제 웹캠에서 사용자 발견)
재학습한 버전.

## v2 실패 원인

glasses_v2는 원본 `seafty_goggles` 데이터셋의 3번째 클래스 `spec`(일반 안경)을 학습에서
아예 **드롭**했다 — `spec`만 있던 이미지는 라벨 없는 배경 이미지로 취급됨. 그 결과 모델은
"이건 고글이 아니다"라는 명시적 대조 신호를 일반 안경에 대해 전혀 받지 못했고, 근접
거리(1m)에서도 confidence 0.6이라는 꽤 높은 확신으로 오탐이 발생함. 원거리 저해상도
문제가 아니라(오히려 1m는 가까운 거리) **모델이 진짜로 두 형태를 구분 못 하는** 근본적인
문제였음.

## 해결 방법 — spec을 배경이 아니라 no_goggles로 재매핑

`spec`을 드롭하지 않고 **`no_goggles`(인덱스 1)로 합쳐서** 재학습:

```python
remap = {goggles_idx: 0, no_goggles_idx: 1, spec_idx: 1}  # spec -> no_goggles
```

이게 단순한 임시방편이 아니라 **SOP 판정 의미상으로도 정확한 매핑**이다 — "일반 안경을
꼈다"와 "아무것도 안 꼈다"는 둘 다 "안전고글을 착용하지 않았다"는 같은 결론이므로, 이
둘을 같은 클래스로 학습시키는 게 오히려 실사용 판정 로직과 정확히 일치한다.

## 학습 설정

| 항목 | 값 |
|---|---|
| 환경 | Google Colab GPU (T4) |
| 모델 | **`glasses_v2_best.pt`에서 warm start** (yolov8n.pt부터 새로 학습하지 않음) |
| 원본 데이터셋 | glasses_v2와 동일(`seafty_goggles` v9) — 라벨 재매핑만 다름 |
| 클래스 | 2개: `goggles`(착용), `no_goggles`(미착용, `no_goggles`+`spec` 합침) |
| epochs | 30 (v2의 50보다 적게 — 이미 goggles 형태를 학습한 가중치에서 시작해 적은 epoch로도 충분할 것으로 판단) |
| 체크포인트 | v2와 동일한 Google Drive 직접 저장(`save_period=10`) + `resume=True` 자동 이어학습 구조 |

- **warm start 효과**: 완전히 새로운 도메인이 아니라 "이미 아는 형태에 새 라벨이 붙은" 수준이라,
  yolov8n.pt(COCO 사전학습)부터 시작하는 것보다 훨씬 빠르게 수렴함. 실제로 30 epoch만에
  v2의 50 epoch 수준 이상의 지표에 도달.

## 클래스 균형 (재매핑 후)

| 클래스 | 인스턴스 수 (근사) |
|---|---|
| goggles | 5,936 |
| no_goggles (기존 no_goggles + spec 합산) | 6,304 |

- v2(5,936 : 4,122, 약 1.44:1)보다 균형이 더 좋아짐(약 1 : 1.06).

## 전체 지표 (epoch 30)

| 지표 | v2 (epoch 50) | **v3 (epoch 30)** |
|---|---|---|
| Precision | 0.917 | **0.934** |
| Recall | 0.926 | **0.920** |
| mAP@50 | 0.974 | **0.974** |
| mAP@50-95 | 0.605 | **0.612** |

## 클래스별 (confusion matrix 기준, 검증셋)

| 클래스 | v2 recall | **v3 recall** |
|---|---|---|
| goggles (착용) | 0.973 | **0.980** |
| no_goggles (미착용, spec 포함) | 0.935 | **0.961** |

- **양쪽 클래스 모두 v2보다 개선** — spec을 대조군으로 명시한 게 단순히 "일반 안경 오탐"만
  고친 게 아니라 전반적인 판별력 자체를 끌어올린 것으로 보임.

## 실물 검증 — v2가 실패했던 실제 문제 재확인 (2026-09-18)

**1. glasses_v1이 실패했던 실물 사진 재검증** (`보안경이미지.png`, 풀페이스 고글):
```
클래스: {0: 'goggles', 1: 'no_goggles'}
보안경이미지.png conf=0.25 -> 1개 검출
  - goggles 0.781   (v2 때는 0.410 — confidence도 상승)
```

**2. v2가 실패했던 실제 문제(1m 거리 일반 안경 오탐)**: 캡처된 이미지가 없어 이 문서에는
아직 재현 테스트 결과를 못 남김 — **실제 웹캠으로 직접 재확인 필요(다음 단계)**.

## webcam_sop.py / webcam_glasses.py 반영

`GLASSES_MODEL_PATH`(webcam_sop.py), `MODEL_PATH`(webcam_glasses.py) 둘 다 `glasses_v3_best.pt`로
전환 완료(2026-09-18). 기존 단위 테스트 5종 재검증 통과.

## 다음 단계

1. [x] Colab 학습 (v2 가중치 warm start, Drive 체크포인트 방식 재사용)
2. [x] 기존 실물 풀페이스 고글 사진으로 회귀 확인 — 문제없음, confidence 상승
3. [x] webcam_sop.py / webcam_glasses.py 모델 경로 전환
4. [ ] **실제 웹캠으로 1m 거리 일반 안경 오탐이 해결됐는지 재확인** (v2에서 발견된 원래 문제)
5. [ ] 실제 웹캠 다양한 거리 · 각도 · 조명에서 종합 테스트
6. [ ] 세정기 현장 실측 시 실제 사용 보호구로 추가 fine-tuning 필요성 재평가

## 산출물

- 가중치: `models/glasses_v3_best.pt` (git 제외 — `*.pt`, 로컬/Drive 보관)
- `docs/glasses_v3/` : results.csv, results.png, confusion_matrix.png
