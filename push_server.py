"""Web Push 알림 프로토타입 서버 — 실제 휴대폰/브라우저로 알림을 받아보기 위한 최소 구현.

기획안 5.5절의 "엣지 PC가 알림 수신용 웹페이지를 제공, 전용 앱 없이 표준 Web Push"
구조를 로컬에서 그대로 재현한다. localhost는 브라우저가 보안 컨텍스트로 취급해
HTTPS 없이도 Push API가 동작한다 (실제 엣지 PC 배포 시엔 HTTPS 필요 — 이건 프로토타입).

준비 (최초 1회):
    python generate_vapid_keys.py

실행:
    uvicorn push_server:app --host 0.0.0.0 --port 8000

사용:
    1. 이 PC와 같은 네트워크의 휴대폰/PC 브라우저로 http://<이 PC의 IP>:8000 접속
       (휴대폰이면 http://localhost 대신 PC의 실제 IP 주소 필요 — ipconfig로 확인.
        단, localhost가 아닌 IP로 접속하면 브라우저가 보안 컨텍스트로 안 봐서
        Push API가 막힐 수 있음 — 그 경우 같은 PC에서 브라우저로 먼저 테스트할 것)
    2. "알림 구독" 버튼 -> 알림 허용
    3. POST /notify 로 테스트 알림 발송, 또는 webcam_sop.py 의 --push-url 로 연동

한계 (프로토타입 수준):
    - 구독 정보는 로컬 JSON 파일에 저장 (실제로는 DB)
    - HTTPS 없음 (localhost 전용). 실제 엣지 PC는 인증서 필요
    - 등급별 차등 발송, 재발송, 반복 억제(기획안 논의 내용) 미구현 — 여기선 "일단 폰으로
      알림이 오는가"만 검증한다
"""

import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from pywebpush import webpush, WebPushException

PRIVATE_KEY_PATH = "vapid_private_key.pem"
PUBLIC_KEY_PATH = "vapid_public_key.txt"
SUBSCRIPTIONS_PATH = "push_subscriptions.json"
VAPID_CLAIMS_SUB = "mailto:example@example.com"  # 실제 서비스면 발신자 연락처로 교체

app = FastAPI(title="SOP 알림 프로토타입")


def load_public_key():
    if not os.path.exists(PUBLIC_KEY_PATH):
        raise RuntimeError(f"{PUBLIC_KEY_PATH} 가 없습니다. python generate_vapid_keys.py 먼저 실행")
    with open(PUBLIC_KEY_PATH, encoding="utf-8") as f:
        return f.read().strip()


def load_subscriptions():
    if not os.path.exists(SUBSCRIPTIONS_PATH):
        return []
    with open(SUBSCRIPTIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_subscriptions(subs):
    with open(SUBSCRIPTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class Subscription(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


class NotifyRequest(BaseModel):
    title: str
    body: str = ""


INDEX_HTML = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOP 알림 프로토타입</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; }
  button { font-size: 16px; padding: 12px 20px; border-radius: 8px; border: none;
           background: #2563eb; color: white; cursor: pointer; width: 100%; margin-top: 12px; }
  button:disabled { background: #9ca3af; }
  #status { margin-top: 16px; padding: 12px; border-radius: 8px; background: #f3f4f6;
            white-space: pre-wrap; font-size: 14px; }
</style>
</head>
<body>
  <h2>작업자 행동인식 SOP - 알림 구독</h2>
  <p>이 페이지에서 구독하면, 편차 발생 시 이 브라우저로 푸시 알림이 옵니다.
     (프로토타입 - 실제 배포 시엔 관리자 휴대폰에서 이 페이지를 홈 화면에 추가)</p>
  <button id="subBtn">알림 구독하기</button>
  <button id="testBtn" disabled>테스트 알림 보내기</button>
  <div id="status">대기 중...</div>

<script>
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

const statusEl = document.getElementById('status');
const subBtn = document.getElementById('subBtn');
const testBtn = document.getElementById('testBtn');

function log(msg) { statusEl.textContent = msg; console.log(msg); }

subBtn.addEventListener('click', async () => {
  try {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      log('이 브라우저는 Web Push를 지원하지 않습니다.');
      return;
    }
    log('서비스 워커 등록 중...');
    const reg = await navigator.serviceWorker.register('/sw.js');
    await navigator.serviceWorker.ready;

    log('알림 권한 요청 중...');
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') { log('알림 권한이 거부되었습니다.'); return; }

    log('구독 키 가져오는 중...');
    const keyRes = await fetch('/vapid-public-key');
    const { publicKey } = await keyRes.json();

    log('푸시 구독 중...');
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });

    const res = await fetch('/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub.toJSON()),
    });
    const data = await res.json();
    log('구독 완료! 서버에 등록된 구독자 수: ' + data.count);
    testBtn.disabled = false;
  } catch (e) {
    log('오류: ' + e);
  }
});

testBtn.addEventListener('click', async () => {
  log('테스트 알림 발송 중...');
  const res = await fetch('/notify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: '테스트 알림', body: '이게 뜨면 성공입니다.' }),
  });
  const data = await res.json();
  log('발송 결과: ' + JSON.stringify(data));
});
</script>
</body>
</html>
"""

SW_JS = """
self.addEventListener('push', event => {
  let data = { title: '알림', body: '' };
  try { data = event.data ? event.data.json() : data; } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      requireInteraction: true,
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


@app.get("/sw.js")
def service_worker():
    return PlainTextResponse(SW_JS, media_type="application/javascript")


@app.get("/vapid-public-key")
def vapid_public_key():
    return {"publicKey": load_public_key()}


@app.post("/subscribe")
def subscribe(sub: Subscription):
    subs = load_subscriptions()
    entry = sub.model_dump()
    if entry not in subs:
        subs.append(entry)
        save_subscriptions(subs)
    return {"status": "ok", "count": len(subs)}


@app.post("/notify")
def notify(req: NotifyRequest):
    subs = load_subscriptions()
    kept = []
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": req.title, "body": req.body}),
                vapid_private_key=PRIVATE_KEY_PATH,
                vapid_claims={"sub": VAPID_CLAIMS_SUB},
            )
            sent += 1
            kept.append(sub)
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                continue  # 만료된 구독 -> 목록에서 제거
            kept.append(sub)  # 일시적 오류로 보고 유지
    if len(kept) != len(subs):
        save_subscriptions(kept)
    return {"sent": sent, "total_subscribers": len(subs)}
