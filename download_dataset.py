"""helmet_v1 데이터셋(hard-hat-detection-ws2wk) 로컬 다운로드 스크립트 — 현재 미사용.

helmet_v2부터는 Colab에서 joseph-nelson/hard-hat-workers 를 받아 학습한다.
이 파일은 초기 로컬 실험 기록으로 남겨둔다. Roboflow 다운로드 방식 참고용.
"""

import os

from roboflow import Roboflow

# API 키는 코드에 직접 넣지 말고 환경변수로 전달하세요.
#   Git Bash:  export ROBOFLOW_API_KEY="본인의_키"
#   그 다음:   python download_dataset.py
api_key = os.environ.get("ROBOFLOW_API_KEY")
if not api_key:
    raise SystemExit(
        "ROBOFLOW_API_KEY 환경변수가 설정되지 않았습니다.\n"
        '설정(Git Bash): export ROBOFLOW_API_KEY="본인의_키"'
    )

rf = Roboflow(api_key=api_key)
project = rf.workspace("adamson-university-nrlyj").project("hard-hat-detection-ws2wk")
version = project.version(1)
dataset = version.download("yolov8", location="datasets/helmet_public")

print("다운로드 완료:", dataset.location)
