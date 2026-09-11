"""위험구역 모서리용 ArUco 마커 4장을 markers/ 에 PNG로 생성한다.

markers/marker_0_TL.png, marker_1_TR.png, marker_2_BR.png, marker_3_BL.png
4장을 출력해서 책상(또는 테스트할 구역) 네 모서리에 시계 방향(TL->TR->BR->BL)
순서로 놓으면 webcam_zone.py 가 그 사각형을 위험구역으로 인식한다.

DICT_4X4_50 사전을 쓴다. webcam_zone.py 와 동일한 사전을 써야 인식된다.
"""

import os

import cv2
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "markers"
MARKER_SIZE = 500          # 마커 자체 픽셀 크기 (출력 시 실제 크기는 프린터 설정에 따름)
CANVAS_MARGIN = 60          # 마커 둘레 흰 여백 (인식률에 중요 — 너무 좁으면 인식 안 됨)
LABEL = {0: "TL (좌상단)", 1: "TR (우상단)", 2: "BR (우하단)", 3: "BL (좌하단)"}

dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

os.makedirs(OUT_DIR, exist_ok=True)

try:
    font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 28)
except OSError:
    font = ImageFont.load_default()

for marker_id, label in LABEL.items():
    marker_img = cv2.aruco.generateImageMarker(dictionary, marker_id, MARKER_SIZE)

    canvas_size = MARKER_SIZE + CANVAS_MARGIN * 2
    canvas = Image.new("L", (canvas_size, canvas_size + 50), 255)
    canvas.paste(Image.fromarray(marker_img), (CANVAS_MARGIN, CANVAS_MARGIN))

    d = ImageDraw.Draw(canvas)
    text = f"ID {marker_id} - {label}"
    tw = d.textlength(text, font=font)
    d.text(((canvas_size - tw) / 2, canvas_size + 8), text, font=font, fill=0)

    path = os.path.join(OUT_DIR, f"marker_{marker_id}_{label.split()[0]}.png")
    canvas.save(path)
    print("생성:", path)

print("\n프린트해서 위험구역 네 모서리에 TL(좌상단)->TR(우상단)->BR(우하단)->BL(좌하단)")
print("순서로(시계 방향) 배치하세요. 마커 둘레 흰 여백을 남기고 출력해야 인식이 잘 됩니다.")
