# helmet_v1 — 헬멧 검출 baseline 학습 결과

공개 데이터셋만으로 안전모 착용/미착용을 검출할 수 있는지 확인하는 1차 실험.

## 학습 설정

| 항목 | 값 |
|---|---|
| 환경 | Google Colab, Tesla T4 (VRAM 16GB) |
| 모델 | `yolov8n.pt` fine-tuning (ultralytics 8.4.144) |
| 데이터셋 | Roboflow `hard-hat-detection-ws2wk` v1 (train 468 / valid 133 / test 67) |
| 클래스 | 3개: `hard hat`, `no hard hat`, `not hard hat` |
| epochs | 50 |
| imgsz | 640 |
| batch | 32 |
| 학습 시간 | 약 7분 (T4) |

## 전체 지표 (epoch 50, valid 기준)

| 지표 | 값 |
|---|---|
| Precision | 0.86 |
| Recall | 0.38 |
| mAP@50 | 0.41 |
| mAP@50-95 | 0.25 |

`hard hat`은 잘 되지만 나머지 두 클래스가 전체 평균을 끌어내림.

## 클래스별 (confusion matrix 기준)

| 클래스 | valid 인스턴스 | 검출(recall) | 비고 |
|---|---|---|---|
| hard hat | 248 | **0.91** | 사용 가능 수준 |
| no hard hat | 15 | 0.33 | 10/15를 background로 놓침 |
| not hard hat | 6 | **0.00** | 모델이 이 클래스를 아예 예측하지 않음 |

`results.png` — 학습 곡선. mAP는 epoch ~30에서 0.41 부근으로 정체, loss는 계속 완만히 하락
(hard hat 쪽에서 조금 더 짜낼 여지는 있으나 소수 클래스가 상한선).

`confusion_matrix.png` — `not hard hat` 행이 통째로 비어 있음(예측 0회).

## 학습 데이터 클래스 불균형

| 클래스 | train 인스턴스 |
|---|---|
| hard hat | 486 |
| no hard hat | 64 |
| not hard hat | 16 |

약 30 : 4 : 1. 소수 클래스 표본이 절대적으로 부족.

## 결론

- **안전모 착용(hard hat) 검출은 공개 데이터로 충분히 가능** (recall 0.91).
- **미착용 검출은 공개 데이터만으로 불가.** 스모크 테스트(3 epoch) → 본 학습(50 epoch, T4)로
  늘려도 `no hard hat`/`not hard hat`은 개선되지 않음 → 학습량이 아니라 **데이터 문제**로 확정.
- 이 시스템에서 실제로 잡아야 하는 건 미착용(=SOP 위반)이므로, **보호구 미착용 항목은 현장
  영상 수집 후 fine-tuning이 필요**하다는 근거 자료가 됨 (기획안의 "1주차 실측에서 항목별
  fine-tuning 필요 여부 확인"에 해당).

## 다음 후보

1. `no hard hat` + `not hard hat` → 미착용 1개 클래스로 통합(2-class) 후 재학습
2. Roboflow Universe 등에서 미착용 이미지 추가 수집
3. 현장 영상 확보 후 소량 라벨링하여 fine-tuning

## 산출물

- 가중치: `models/helmet_v1_best.pt` (git 제외 — `*.pt`, 로컬/Drive 보관)
- Colab 노트북: (Drive 저장) — 재학습 시 참조
