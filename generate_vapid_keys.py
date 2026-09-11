"""Web Push용 VAPID 키 쌍 생성 — 최초 1회만 실행.

VAPID(Voluntary Application Server Identification)는 우리 서버가 누구인지 브라우저
푸시 서비스(FCM/Mozilla 등)에 증명하는 서명 키다. 전용 앱 없이 표준 Web Push를
쓰기로 한 기획(5.5절)의 실제 구현에 필요하다.

생성물:
  vapid_private_key.pem  — 서버가 알림 서명에 쓰는 비공개 키. 절대 커밋하지 않는다.
  vapid_public_key.txt   — 브라우저가 구독할 때 쓰는 공개 키. 공개돼도 무방.
"""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02

PRIVATE_PATH = "vapid_private_key.pem"
PUBLIC_PATH = "vapid_public_key.txt"

vapid = Vapid02()
vapid.generate_keys()
vapid.save_key(PRIVATE_PATH)

public_bytes = vapid.public_key.public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
)
public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode()
with open(PUBLIC_PATH, "w", encoding="utf-8") as f:
    f.write(public_b64)

print("생성 완료:")
print(" -", PRIVATE_PATH, "(비공개, 서버 전용. .gitignore에 포함돼 있는지 확인)")
print(" -", PUBLIC_PATH)
print("공개 키:", public_b64)
