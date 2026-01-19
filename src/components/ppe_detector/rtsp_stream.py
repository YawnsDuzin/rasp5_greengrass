#!/usr/bin/env python3
"""
RTSP Stream Reader
RTSP 프로토콜로 IP 카메라 스트림을 수신하는 모듈
"""

import logging
import time
from threading import Thread, Lock, Event
from queue import Queue, Empty

import cv2
import numpy as np

logger = logging.getLogger('RTSPStreamReader')


class RTSPStreamReader:
    """RTSP 스트림 리더 - 비동기 프레임 읽기 지원"""

    def __init__(
        self,
        rtsp_url: str,
        timeout: int = 30,
        reconnect_delay: int = 5,
        buffer_size: int = 2,
        resize: tuple = None
    ):
        """
        Args:
            rtsp_url: RTSP 스트림 URL
                예: rtsp://admin:password@192.168.1.100:554/stream1
            timeout: 연결 타임아웃 (초)
            reconnect_delay: 재연결 대기 시간 (초)
            buffer_size: 프레임 버퍼 크기
            resize: 프레임 리사이즈 (width, height) 또는 None
        """
        self.rtsp_url = rtsp_url
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.buffer_size = buffer_size
        self.resize = resize

        self.cap = None
        self.frame_queue = Queue(maxsize=buffer_size)
        self.lock = Lock()
        self.running = Event()
        self.connected = Event()
        self.read_thread = None

        # 통계
        self.stats = {
            'frames_read': 0,
            'frames_dropped': 0,
            'reconnects': 0,
            'errors': 0
        }

    def connect(self) -> bool:
        """RTSP 스트림에 연결"""
        logger.info(f"Connecting to RTSP stream: {self._mask_url(self.rtsp_url)}")

        try:
            # OpenCV VideoCapture 설정
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

            # 버퍼 크기 최소화 (지연 감소)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 연결 타임아웃 설정
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.timeout * 1000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.timeout * 1000)

            # RTSP 전송 프로토콜 설정 (TCP 권장)
            # 0 = auto, 1 = TCP, 2 = UDP
            # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))

            if not self.cap.isOpened():
                logger.error("Failed to open RTSP stream")
                return False

            # 스트림 정보 로깅
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(f"Connected! Stream info: {width}x{height} @ {fps:.1f} FPS")

            # 첫 프레임 읽기 테스트
            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.error("Failed to read initial frame")
                return False

            self.connected.set()

            # 비동기 읽기 스레드 시작
            self._start_read_thread()

            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.stats['errors'] += 1
            return False

    def _start_read_thread(self):
        """프레임 읽기 스레드 시작"""
        self.running.set()
        self.read_thread = Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        logger.info("Frame read thread started")

    def _read_loop(self):
        """프레임 읽기 루프 (백그라운드 스레드)"""
        while self.running.is_set():
            try:
                with self.lock:
                    if self.cap is None or not self.cap.isOpened():
                        self.connected.clear()
                        time.sleep(0.1)
                        continue

                    ret, frame = self.cap.read()

                if not ret or frame is None:
                    logger.warning("Failed to read frame")
                    self.stats['errors'] += 1
                    time.sleep(0.1)
                    continue

                # 리사이즈 (필요 시)
                if self.resize:
                    frame = cv2.resize(frame, self.resize)

                # 큐가 가득 차면 오래된 프레임 제거
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                        self.stats['frames_dropped'] += 1
                    except Empty:
                        pass

                self.frame_queue.put(frame)
                self.stats['frames_read'] += 1

            except Exception as e:
                logger.error(f"Read loop error: {e}")
                self.stats['errors'] += 1
                time.sleep(0.1)

    def read_frame(self, timeout: float = 1.0) -> np.ndarray:
        """
        프레임 읽기

        Args:
            timeout: 대기 시간 (초)

        Returns:
            np.ndarray: BGR 형식의 프레임 또는 None
        """
        if not self.connected.is_set():
            return None

        try:
            frame = self.frame_queue.get(timeout=timeout)
            return frame
        except Empty:
            return None

    def reconnect(self) -> bool:
        """스트림 재연결"""
        logger.info("Attempting to reconnect...")
        self.stats['reconnects'] += 1

        # 기존 연결 정리
        self.running.clear()
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)

        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

        self.connected.clear()

        # 큐 비우기
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break

        # 재연결 대기
        time.sleep(self.reconnect_delay)

        # 재연결 시도
        return self.connect()

    def release(self):
        """리소스 해제"""
        logger.info("Releasing RTSP stream resources...")

        self.running.clear()

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=3)

        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

        self.connected.clear()
        logger.info(f"Released. Stats: {self.stats}")

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.connected.is_set()

    def get_stats(self) -> dict:
        """통계 반환"""
        return self.stats.copy()

    def _mask_url(self, url: str) -> str:
        """URL에서 비밀번호 마스킹"""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)


class TestStreamReader(RTSPStreamReader):
    """테스트용 스트림 리더 - USB 웹캠 또는 파일 사용"""

    def __init__(self, source=0, **kwargs):
        """
        Args:
            source: 카메라 인덱스 (0, 1, ...) 또는 비디오 파일 경로
        """
        super().__init__(rtsp_url=str(source), **kwargs)
        self.source = source

    def connect(self) -> bool:
        """로컬 카메라/파일에 연결"""
        logger.info(f"Connecting to test source: {self.source}")

        try:
            self.cap = cv2.VideoCapture(self.source)

            if not self.cap.isOpened():
                logger.error("Failed to open video source")
                return False

            # 스트림 정보
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(f"Connected! Source info: {width}x{height} @ {fps:.1f} FPS")

            self.connected.set()
            self._start_read_thread()

            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False


# 테스트 코드
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='RTSP Stream Reader Test')
    parser.add_argument('--url', type=str, default='0',
                        help='RTSP URL or camera index (default: 0 for webcam)')
    parser.add_argument('--show', action='store_true',
                        help='Show video window')
    args = parser.parse_args()

    # 테스트 실행
    if args.url.isdigit():
        reader = TestStreamReader(source=int(args.url))
    else:
        reader = RTSPStreamReader(rtsp_url=args.url)

    if reader.connect():
        print("Connected successfully!")

        frame_count = 0
        start_time = time.time()

        try:
            while True:
                frame = reader.read_frame()
                if frame is not None:
                    frame_count += 1

                    if args.show:
                        cv2.imshow('RTSP Stream', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

                    # FPS 출력
                    if frame_count % 30 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        print(f"FPS: {fps:.1f}, Frames: {frame_count}, Stats: {reader.get_stats()}")

        except KeyboardInterrupt:
            print("\nInterrupted")

        finally:
            reader.release()
            cv2.destroyAllWindows()
    else:
        print("Failed to connect")
