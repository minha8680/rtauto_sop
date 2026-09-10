# helmet_v2 — 착용/미착용 2클래스 학습 결과

helmet_v1에서 미착용 검출이 실패한 원인(미착용 학습 데이터 부족)을 해결하기 위해,
미착용(`head`) 데이터가 풍부한 공개 데이터셋으로 교체하여 재학습.

## 학습 설정

| 항목 | 값 |
|---|---|
| 환경 | Google Colab GPU |
| 모델 | `yolov8n.pt` fine-tuning |
| 데이터셋 | Roboflow `joseph-nelson/hard-hat-workers` (~7,000장) |
| 클래스 | 2개: `helmet`(착용), `no_helmet`(미착용) — 원본 `person` 클래스는 제외 |
| epochs | 50 |
| 학습 시간 | 약 3.4시간 (results.csv `time` 기준) |

> 원본 데이터셋의 `head` → `no_helmet`, `hard hat`/`helmet` → `helmet` 로 재매핑, `person` 라벨 제거.

## 전체 지표 (epoch 50)

| 지표 | helmet_v1 | **helmet_v2** |
|---|---|---|
| Precision | 0.86 | **0.95** |
| Recall | 0.38 | **0.93** |
| mAP@50 | 0.41 | **0.96** |
| mAP@50-95 | 0.25 | **0.65** |

## 클래스별 (confusion matrix 기준)

| 클래스 | 인스턴스 | 검출(recall) | v1 대비 |
|---|---|---|---|
| helmet (착용) | 3,913 | **0.97** | v1 hard hat 0.91 → 유지·개선 |
| no_helmet (미착용) | 1,339 | **0.95** | v1 no hard hat 0.33 / not hard hat 0.00 → **대폭 개선** |

- `no_helmet` 미검출: 1,339개 중 65개(48개는 background로, 17개는 helmet으로 오인)
- background를 객체로 오인한 오탐: helmet 346건, no_helmet 183건 (conf 임계값 조정 여지)

## 학습 곡선 (results.png)

- train/val loss 모두 정상 하락 후 정체, **과적합 징후 없음** (val loss가 다시 오르지 않음)
- mAP50은 epoch ~25에서 0.96 도달 후 안정
- v1과 달리 소수 클래스가 없어 전체 지표가 실제 성능을 그대로 반영

## 결론

- **착용/미착용 검출 모두 실용 수준 달성** (recall 0.95~0.97).
- helmet_v1 대비 유일한 변경은 **데이터셋 교체**(미착용 표본 16~64개 → 1,000개 이상).
  학습 설정(모델, epochs)은 동일 → **"학습량이 아니라 데이터 문제였다"는 helmet_v1 결론을 재확인**.
- 이 시스템의 핵심 판정 대상인 **보호구 미착용(SOP 위반) 검출이 공개 데이터로 가능**함을 확인.
  단, 현장 조건(바디캠 화각·거리·조도, 세정기 작업 환경)에서의 성능은 1주차 실측으로 별도 검증 필요.

## 다음 단계

1. 로컬 웹캠 실시간 테스트 (착용/미착용 전환, conf 임계값 튜닝)
2. `models/helmet_v2_best.pt` 를 검출 파이프라인의 보호구 착용 판정 모듈로 사용
3. 인원 수 검출(person, COCO 사전학습) + 추적(ByteTrack) 착수

## 산출물

- 가중치: `models/helmet_v2_best.pt` (git 제외 — `*.pt`, 로컬/Drive 보관)
- `docs/helmet_v2/` : results.csv, results.png, confusion_matrix.png
