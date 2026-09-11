"""ArUco 마커 인식 진단용 — webcam_zone.py 로직 없이 "마커가 보이는가"만 확인.

카메라 화면에 인식된 마커 테두리와 ID를 그려서 보여주고, 콘솔에도 실시간으로
몇 개가 잡히는지 찍는다. 마커가 안 잡히면 여기서부터 원인을 좁혀나간다.
"""

import cv2

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(DICT, params)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("카메라를 열 수 없습니다.")
    exit()

last_ids = None

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, rejected = detector.detectMarkers(gray)

    cv2.aruco.drawDetectedMarkers(frame, corners, ids)

    ids_list = sorted(ids.flatten().tolist()) if ids is not None else []
    if ids_list != last_ids:
        print(f"검출된 마커 ID: {ids_list}   (후보였다가 탈락한 것: {len(rejected)}개)")
        last_ids = ids_list

    cv2.putText(frame, f"detected: {ids_list}", (12, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"rejected candidates: {len(rejected)}", (12, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)

    cv2.imshow("ArUco 진단 (q: 종료)", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
