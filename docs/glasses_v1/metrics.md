# glasses_v1 — 보안경 착용/미착용 2클래스 학습 결과

helmet_v2와 같은 방식: 클래스 균형이 잘 맞는 공개 데이터셋에서 관련 없는 클래스를 제거하고
착용/미착용 2클래스만 남겨 학습. helmet_v1→v2 때와 달리 처음부터 균형 잡힌 데이터로 시작.

## 학습 설정

| 항목 | 값 |
|---|---|
| 환경 | Google Colab GPU (T4) |
| 모델 | `yolov8n.pt` fine-tuning |
| 원본 데이터셋 | Roboflow [Personal Protective Equipment - Combined Model](https://universe.roboflow.com/roboflow-universe-projects/personal-protective-equipment-combined-model) (44,002장, 14클래스) |
| 클래스 | 2개: `glasses`(착용), `no_glasses`(미착용) — 나머지 12개 클래스(Mask/Person/Hardhat/Ladder/Safety Vest/Fall-Detected/Gloves/Safety Cone 등) 제거 |
| 재매핑 방법 | Roboflow "Modify Classes" 전처리가 유료 기능이라, 다운로드 후 라벨 `.txt`를 스크립트로 필터링 (Goggles→0, NO-Goggles→1, 나머지 클래스 라인 삭제) — `data.yaml`도 `nc: 2`로 수정 |
| epochs | 50 |
| 학습 시간 | 약 61분 (results.csv `time` 기준, epoch 50 = 3659초) — helmet_v2(약 3.4시간)보다 훨씬 빠름 |

## 클래스 균형 (재매핑 전, Roboflow "Classes & Tags" 기준)

| 클래스 | 인스턴스 수 |
|---|---|
| Goggles (→ glasses) | 4,188 |
| NO-Goggles (→ no_glasses) | 4,092 |

- helmet_v1이 실패했던 원인(미착용 표본 16~64개)과 달리 **처음부터 두 클래스가 거의 1:1로 균형** —
  클래스 불균형 문제 자체가 없었음.

## 전체 지표 (epoch 50)

| 지표 | 값 |
|---|---|
| Precision | 0.899 |
| Recall | 0.928 |
| mAP@50 | **0.970** |
| mAP@50-95 | 0.585 |

(참고: epoch 45가 mAP50 0.971로 근소하게 더 높았음 — 45~50 구간에서 사실상 수렴)

## 클래스별 (confusion matrix 기준, 검증셋)

| 클래스 | 실제 인스턴스 | 정답 예측 | Recall | 배경 오인식(놓침) | 반대 클래스 오분류 |
|---|---|---|---|---|---|
| glasses (착용) | 827 | 807 | **0.976** | 19 | 1 (no_glasses로 오분류) |
| no_glasses (미착용) | 859 | 818 | **0.952** | 33 | 8 (glasses로 오분류) |

- 배경을 객체로 오인한 오탐(false positive): glasses 111건, no_glasses 149건 — helmet_v2와 비슷한
  수준의 배경 오탐. conf 임계값 조정 여지 있음 (helmet_v2도 동일 이슈, `HELMET_CONF=0.5` 적용 중)

## 학습 곡선 (results.png)

- helmet_v2와 마찬가지로 val loss가 다시 오르지 않음 — **과적합 징후 없음**
- mAP50이 epoch 30 전후로 이미 0.96대에 도달, 이후 완만하게 개선되며 수렴

## 결론

- **착용/미착용 검출 모두 실용 수준 달성** (recall 0.95~0.98), helmet_v2와 거의 동급 성능.
- 데이터셋 단계에서 클래스 균형을 미리 확인(4,188 vs 4,092)하고 시작한 덕에 helmet_v1이 겪었던
  실패를 처음부터 피함 — "학습 전 클래스 균형 확인"이 helmet 실험에서 얻은 교훈의 재확인.
- 다만 이 데이터셋은 건설현장 등 일반 산업현장 사진 위주라, **세정기 작업 환경(실내, 근접)에서도
  똑같이 잘 되는지는 웹캠 실측으로 별도 확인 필요** (helmet_v2도 겪었던 것과 같은 한계).

## 다음 단계

1. 로컬 웹캠 실시간 테스트 (착용/미착용 전환, conf 임계값 튜닝) — `webcam_glasses.py`
2. `webcam_sop.py`의 "보호구 착용" 판정에 helmet과 함께 통합할지, 별도 규칙으로 둘지 결정
3. 통합 시 helmet과 마찬가지로 person 박스와의 공간 매칭(박스 중심점 포함 여부)으로
   "검출=착용" 오류 방지 로직 재사용

## 산출물

- 가중치: `models/glasses_v1_best.pt` (git 제외 — `*.pt`, 로컬/Drive 보관)
- `docs/glasses_v1/` : results.csv, results.png, confusion_matrix.png
