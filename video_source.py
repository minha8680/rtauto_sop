# -*- coding: utf-8 -*-
"""영상 입력(웹캠/RTSP)을 여는 공통 헬퍼 — webcam_sop.py, rtsp_test.py가 공유한다.

RTSP 관련 설정(버퍼·타임아웃)을 한 곳에만 두어, 두 파일에 따로 복사해두면 나중에 한쪽만
고치고 잊어버리는 사고(설정 드리프트)를 막는다. 검출 로직과는 완전히 무관 — 영상 "입수"만
담당하고, 그 뒤로 나오는 frame이 어디서 왔는지는 호출하는 쪽이 신경 쓸 필요 없다
(webcam_sop.py의 `_run()`이 frame만 받는 구조와 같은 이유).

나중에 작업자캠+감시단원캠 2채널을 동시에 받는 구조로 갈 때도, 채널마다 이 함수를 한 번씩
불러서 cap 두 개를 만드는 식으로 그대로 재사용할 수 있게 설계했다.
"""
import cv2

RTSP_BUFFERSIZE = 1
RTSP_OPEN_TIMEOUT_MSEC = 8000   # FFmpeg 빌드에 따라 정확히 안 지켜질 수 있음(rtsp_test.py로 확인됨)
RTSP_READ_TIMEOUT_MSEC = 8000


def open_video_source(source):
    """source가 정수 문자열("0" 등)이면 로컬 웹캠, rtsp://·rtsps:// 로 시작하면 RTSP
    스트림으로 연다.

    RTSP일 때만 저지연 버퍼(CAP_PROP_BUFFERSIZE=1) + 연결/읽기 타임아웃을 적용한다. 기본
    버퍼링을 그대로 두면 처리 속도가 스트림 속도를 못 따라갈 때 화면이 점점 과거 프레임을
    보여주는 지연 누적 문제가 생기기 때문이다(OpenCV+RTSP에서 흔한 문제).
    """
    source = str(source)
    if source.lower().startswith(("rtsp://", "rtsps://")):
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, RTSP_BUFFERSIZE)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, RTSP_OPEN_TIMEOUT_MSEC)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, RTSP_READ_TIMEOUT_MSEC)
        return cap
    return cv2.VideoCapture(int(source))  # 웹캠 장치 번호
