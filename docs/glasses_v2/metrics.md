# glasses_v2 — 보안경 착용/미착용 재학습 (풀페이스 고글 스타일 보강)

glasses_v1(2026-09-14)이 실물 검증(풀페이스 단일렌즈 스플래시 고글, 실물 + 프린트 둘 다)에서
완전히 인식 실패한 문제를 해결하기 위해 새 데이터셋으로 재학습한 버전.

## 실패 원인 재확인

glasses_v1은 Roboflow "Personal Protective Equipment - Combined Model"에서 `Goggles`/
`NO-Goggles`만 필터링해 썼는데, 클래스명은 "Goggles"였지만 실제 이미지가 일반 안경형
위주였던 것으로 추정 — CONF를 0.01까지 낮춰도 실물 풀페이스 고글 사진에서 검출 0건
(2026-09-17 확인). "클래스 이름만 보고 데이터 내용을 확인 안 한" 것이 원인.

## 데이터셋 선정 — 이번엔 인스턴스 수 + 실제 이미지 스타일을 먼저 확인

Roboflow Universe에서 "goggles" 관련 후보를 검색한 결과, 상당수가 이름만 다르고 사실상
같은 원본 데이터(인스턴스 수가 거의 일치)였음 — `roboflow-universe-projects/eye-protection`,
`personal-protective-equipment/ppes-kaxsi`, `mohamed-traore-2ekkp/ppe-detection-l80fg` 전부
Goggles≈4,184~4,188 / NO-Goggles≈4,092로 동일 계열. 이 중 아무거나 골랐으면 같은 실패를
반복했을 것.

`abduls-okhnp/seafty_goggles`만 유일하게 다른 규모의 데이터(Goggles 5,936 / NO-Goggles
4,122 / spec 2,182)였고, 프로젝트 아이콘 썸네일 확인 + 사용자가 브라우저로 직접 이미지를
훑어봐서 풀페이스 고글이 실제로 섞여 있음을 확인한 뒤 학습을 진행함(2026-09-17).

**클래스 이름 자체가 `goggles`/`no_goggles`/`spec`(일반 안경)으로 이미 분리돼 있다는 점이
핵심** — glasses_v1이 뭉뚱그렸을 가능성이 있는 "일반 안경 vs 고글" 구분을 원본 데이터셋에서
이미 해뒀다는 뜻이라, `spec`만 빼고 학습하면 오염이 줄어들 것으로 판단.

## 학습 설정

| 항목 | 값 |
|---|---|
| 환경 | Google Colab GPU (T4) |
| 모델 | `yolov8n.pt` fine-tuning |
| 원본 데이터셋 | Roboflow [seafty_goggles](https://universe.roboflow.com/abduls-okhnp/seafty_goggles) (v9, 9,149장, CC BY 4.0) |
| 클래스 | 2개: `goggles`(착용), `no_goggles`(미착용) — 원본의 `spec`(일반 안경) 클래스는 라벨 스크립트로 제거 |
| 재매핑 방법 | glasses_v1과 동일한 방식(라벨 `.txt` 필터링 스크립트) — 이번엔 원본 클래스명을 `data.yaml`에서 직접 읽어 인덱스를 찾으므로 클래스 순서가 달라져도 안전 |
| epochs | 50 |
| 체크포인트 | Google Drive에 직접 저장(`save_period=10`) + 세션 끊김 시 `resume=True`로 자동 이어학습 — 이번 세션부터 도입한 방식 |

## 클래스 균형 (재매핑 전, Roboflow API로 직접 조회)

| 클래스 | 인스턴스 수 |
|---|---|
| goggles | 5,936 |
| no_goggles | 4,122 |
| (spec, 제외) | 2,182 |

- 비율 약 1.44 : 1 — glasses_v1(4,188:4,092, 거의 1:1)보다는 덜 균형적이지만 helmet_v1이
  실패했던 수준(16~64개)과는 차원이 다름.
- 인스턴스 수는 Roboflow 프로젝트 페이지를 스크래핑하는 대신 `https://api.roboflow.com/
  {workspace}/{project}?api_key=...`를 직접 호출해 `classes` 필드로 정확히 확인함 —
  페이지가 막대그래프 등 텍스트로 안 나오는 값도 이 방법으로 조회 가능(2026-09-17 확립한
  방법, 다음에 데이터셋 확인할 때도 이 방법 먼저 쓸 것).

## 전체 지표 (epoch 50, epoch 47이 mAP50 0.974로 근소하게 더 높음)

| 지표 | 값 (epoch 50) |
|---|---|
| Precision | 0.917 |
| Recall | 0.926 |
| mAP@50 | **0.974** |
| mAP@50-95 | 0.605 |

## 클래스별 (confusion matrix 기준, 검증셋)

| 클래스 | 실제 인스턴스 | 정답 예측 | Recall |
|---|---|---|---|
| goggles (착용) | 1,170 (1138+3+29) | 1,138 | **0.973** |
| no_goggles (미착용) | 844 (9+789+46) | 789 | **0.935** |

- 배경 오인식(false positive): goggles로 오탐 123건, no_goggles로 오탐 137건 —
  glasses_v1/helmet_v2와 비슷한 수준.

## 학습 곡선 (results.png)

- val loss가 계속 감소, mAP50/precision/recall 전부 우상향 후 수렴 — 과적합 징후 없음.
- glasses_v1과 마찬가지로 40 epoch 이후로는 개선 폭이 완만해짐.

## 실물 검증 — glasses_v1이 실패했던 바로 그 이미지로 재확인 (2026-09-17)

`glasses_v1`이 conf=0.01까지 낮춰도 0건 검출이었던 실물 보안고글 사진(`보안경이미지.png`,
사용자가 실제 사용 중인 제품)을 `glasses_v2`로 다시 테스트:

```
클래스: {0: 'goggles', 1: 'no_goggles'}
보안경이미지.png conf=0.25 -> 1개 검출
  - goggles 0.410
```

**성공** — 박스도 고글 전체를 정확히 감쌈(annotated 이미지로 육안 확인). 새 데이터셋이
실제 문제를 해결했음을 확인.

## webcam_sop.py / webcam_glasses.py 반영

`GLASSES_MODEL_PATH`(webcam_sop.py), `MODEL_PATH`(webcam_glasses.py) 둘 다 `glasses_v2_best.pt`로
전환 완료(2026-09-17). glasses_v1 가중치는 로컬에 남겨두되(비교용) 실사용은 v2로 넘어감.

## 다음 단계

1. [x] Colab 학습 (Drive 체크포인트 + 자동 이어학습 방식으로 진행)
2. [x] 실물 이미지로 재검증 — glasses_v1 실패 사례 해결 확인
3. [x] webcam_sop.py / webcam_glasses.py 모델 경로 전환
4. [ ] 실제 웹캠으로 실시간 테스트 (조명 · 각도 · 거리 조건에서 안정적으로 잡히는지)
5. [ ] 세정기 현장 실측 시 실제 사용 보호구로 추가 fine-tuning 필요성 재평가

## 산출물

- 가중치: `models/glasses_v2_best.pt` (git 제외 — `*.pt`, 로컬/Drive 보관)
- `docs/glasses_v2/` : results.csv, results.png, confusion_matrix.png
