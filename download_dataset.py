import os

from roboflow import Roboflow

# API 키는 코드에 직접 넣지 말고 환경변수로 전달하세요.
#   PowerShell:  $env:ROBOFLOW_API_KEY = "본인의_키"
#   그 다음:     python download_dataset.py
api_key = os.environ.get("ROBOFLOW_API_KEY")
if not api_key:
    raise SystemExit(
        "ROBOFLOW_API_KEY 환경변수가 설정되지 않았습니다.\n"
        '설정: $env:ROBOFLOW_API_KEY = "본인의_키"'
    )

rf = Roboflow(api_key=api_key)
project = rf.workspace("adamson-university-nrlyj").project("hard-hat-detection-ws2wk")
version = project.version(1)
dataset = version.download("yolov8", location="datasets/helmet_public")

print("다운로드 완료:", dataset.location)
