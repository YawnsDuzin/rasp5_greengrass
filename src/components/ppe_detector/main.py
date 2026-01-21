#!/usr/bin/env python3
"""
PPE Detector - AWS IoT Greengrass Component
라즈베리파이5에서 RTSP 카메라 스트림을 받아 PPE 착용 여부를 감지합니다.
"""

import json
import logging
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from threading import Event

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PPEDetector')

# Greengrass IPC 클라이언트
try:
    import awsiot.greengrasscoreipc as ipc
    from awsiot.greengrasscoreipc.model import (
        PublishToIoTCoreRequest,
        QOS
    )
    GREENGRASS_IPC_AVAILABLE = True
except ImportError:
    logger.warning("Greengrass IPC not available. Running in standalone mode.")
    GREENGRASS_IPC_AVAILABLE = False

from rtsp_stream import RTSPStreamReader
from ppe_model import PPEDetector
from mqtt_publisher import MQTTPublisher


class PPEDetectorComponent:
    """PPE 인식 Greengrass 컴포넌트 메인 클래스"""

    def __init__(self):
        self.shutdown_event = Event()
        self.config = self._load_config()

        # 컴포넌트 초기화
        self.stream_reader = None
        self.ppe_detector = None
        self.mqtt_publisher = None

        # 통계
        self.stats = {
            'frames_processed': 0,
            'detections': 0,
            'alerts_sent': 0,
            'start_time': None
        }

        # 시그널 핸들러 등록
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _load_config(self) -> dict:
        """설정 로드 - 환경 변수 또는 기본값 사용"""
        config = {
            # RTSP 설정
            'rtsp_url': os.environ.get('RTSP_URL', 'rtsp://192.168.1.100:554/stream'),
            'rtsp_timeout': int(os.environ.get('RTSP_TIMEOUT', '30')),
            'rtsp_reconnect_delay': int(os.environ.get('RTSP_RECONNECT_DELAY', '5')),

            # 모델 설정 (OpenCV DNN + ONNX)
            'model_path': os.environ.get('MODEL_PATH', '/opt/ppe-detector/models/yolov8n.onnx'),
            'confidence_threshold': float(os.environ.get('CONFIDENCE_THRESHOLD', '0.5')),
            'use_cuda': os.environ.get('USE_CUDA', 'false').lower() == 'true',  # GPU 사용 여부

            # 처리 설정
            'process_interval': float(os.environ.get('PROCESS_INTERVAL', '1.0')),  # 초
            'skip_frames': int(os.environ.get('SKIP_FRAMES', '5')),  # 프레임 건너뛰기

            # MQTT 설정
            'alert_topic': os.environ.get('ALERT_TOPIC', 'ppe/alerts'),
            'status_topic': os.environ.get('STATUS_TOPIC', 'ppe/status'),
            'detection_topic': os.environ.get('DETECTION_TOPIC', 'ppe/detections'),

            # 알림 설정
            'alert_cooldown': int(os.environ.get('ALERT_COOLDOWN', '30')),  # 동일 알림 최소 간격 (초)
            'required_ppe': os.environ.get('REQUIRED_PPE', 'hardhat,safety_vest').split(','),

            # Thing 이름
            'thing_name': os.environ.get('AWS_IOT_THING_NAME', 'RaspberryPi5-PPE'),
        }

        logger.info(f"Configuration loaded: {json.dumps(config, indent=2)}")
        return config

    def _signal_handler(self, signum, frame):
        """시그널 핸들러 - 정상 종료 처리"""
        logger.info(f"Received signal {signum}. Shutting down...")
        self.shutdown_event.set()

    def initialize(self):
        """컴포넌트 초기화"""
        logger.info("Initializing PPE Detector Component...")

        # RTSP 스트림 리더 초기화
        self.stream_reader = RTSPStreamReader(
            rtsp_url=self.config['rtsp_url'],
            timeout=self.config['rtsp_timeout'],
            reconnect_delay=self.config['rtsp_reconnect_delay']
        )

        # PPE 감지 모델 초기화 (OpenCV DNN + ONNX)
        self.ppe_detector = PPEDetector(
            model_path=self.config['model_path'],
            confidence_threshold=self.config['confidence_threshold'],
            use_cuda=self.config['use_cuda']
        )

        # MQTT 퍼블리셔 초기화
        self.mqtt_publisher = MQTTPublisher(
            thing_name=self.config['thing_name'],
            use_greengrass_ipc=GREENGRASS_IPC_AVAILABLE
        )

        logger.info("PPE Detector Component initialized successfully")

    def run(self):
        """메인 실행 루프"""
        logger.info("Starting PPE detection loop...")
        self.stats['start_time'] = datetime.now()

        # 상태 메시지 발행
        self._publish_status("RUNNING")

        last_process_time = 0
        frame_count = 0
        last_alerts = {}  # 클래스별 마지막 알림 시간

        try:
            # 스트림 연결
            if not self.stream_reader.connect():
                logger.error("Failed to connect to RTSP stream")
                self._publish_status("ERROR", "RTSP connection failed")
                return

            while not self.shutdown_event.is_set():
                # 프레임 읽기
                frame = self.stream_reader.read_frame()
                if frame is None:
                    logger.warning("Failed to read frame, attempting reconnection...")
                    time.sleep(self.config['rtsp_reconnect_delay'])
                    self.stream_reader.reconnect()
                    continue

                frame_count += 1

                # 프레임 건너뛰기
                if frame_count % self.config['skip_frames'] != 0:
                    continue

                # 처리 간격 체크
                current_time = time.time()
                if current_time - last_process_time < self.config['process_interval']:
                    continue

                last_process_time = current_time

                # PPE 감지 수행
                detections = self.ppe_detector.detect(frame)
                self.stats['frames_processed'] += 1

                if detections:
                    self.stats['detections'] += len(detections)

                    # 감지 결과 발행
                    self._publish_detection(detections)

                    # PPE 미착용 확인 및 알림
                    alerts = self._check_ppe_compliance(detections, last_alerts, current_time)
                    if alerts:
                        self._publish_alerts(alerts)
                        last_alerts.update({a['class']: current_time for a in alerts})

                # 주기적 상태 보고 (1분마다)
                if self.stats['frames_processed'] % 60 == 0:
                    self._publish_status("RUNNING")

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            logger.error(traceback.format_exc())
            self._publish_status("ERROR", str(e))

        finally:
            self.cleanup()

    def _check_ppe_compliance(self, detections: list, last_alerts: dict, current_time: float) -> list:
        """PPE 착용 규정 준수 확인"""
        alerts = []

        # 감지된 사람 수
        persons = [d for d in detections if d['class'] == 'person']

        for person in persons:
            person_box = person['bbox']

            # 해당 사람 영역 내 PPE 확인
            detected_ppe = set()
            for d in detections:
                if d['class'] in self.config['required_ppe']:
                    # 바운딩 박스 겹침 확인 (간단한 IoU)
                    if self._boxes_overlap(person_box, d['bbox']):
                        detected_ppe.add(d['class'])

            # 누락된 PPE 확인
            missing_ppe = set(self.config['required_ppe']) - detected_ppe

            for ppe in missing_ppe:
                # 쿨다운 체크
                if ppe in last_alerts:
                    if current_time - last_alerts[ppe] < self.config['alert_cooldown']:
                        continue

                alerts.append({
                    'class': ppe,
                    'type': 'missing_ppe',
                    'message': f'PPE 미착용 감지: {ppe}',
                    'person_bbox': person_box,
                    'confidence': person['confidence']
                })

        return alerts

    def _boxes_overlap(self, box1: list, box2: list, threshold: float = 0.3) -> bool:
        """두 바운딩 박스의 겹침 여부 확인"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        if x2 <= x1 or y2 <= y1:
            return False

        intersection = (x2 - x1) * (y2 - y1)
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

        return (intersection / box2_area) > threshold if box2_area > 0 else False

    def _publish_detection(self, detections: list):
        """감지 결과 MQTT 발행"""
        message = {
            'timestamp': datetime.now().isoformat(),
            'thing_name': self.config['thing_name'],
            'detections': detections,
            'count': len(detections)
        }

        self.mqtt_publisher.publish(
            topic=self.config['detection_topic'],
            payload=message
        )

    def _publish_alerts(self, alerts: list):
        """알림 MQTT 발행"""
        for alert in alerts:
            message = {
                'timestamp': datetime.now().isoformat(),
                'thing_name': self.config['thing_name'],
                'alert_type': alert['type'],
                'missing_ppe': alert['class'],
                'message': alert['message'],
                'severity': 'HIGH',
                'location': {
                    'bbox': alert.get('person_bbox', [])
                }
            }

            self.mqtt_publisher.publish(
                topic=self.config['alert_topic'],
                payload=message
            )

            self.stats['alerts_sent'] += 1
            logger.warning(f"ALERT: {alert['message']}")

    def _publish_status(self, status: str, error_message: str = None):
        """상태 MQTT 발행"""
        message = {
            'timestamp': datetime.now().isoformat(),
            'thing_name': self.config['thing_name'],
            'status': status,
            'stats': {
                'frames_processed': self.stats['frames_processed'],
                'detections': self.stats['detections'],
                'alerts_sent': self.stats['alerts_sent'],
                'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds()
                    if self.stats['start_time'] else 0
            }
        }

        if error_message:
            message['error'] = error_message

        self.mqtt_publisher.publish(
            topic=self.config['status_topic'],
            payload=message
        )

        logger.info(f"Status: {status}, Stats: {self.stats}")

    def cleanup(self):
        """리소스 정리"""
        logger.info("Cleaning up resources...")

        if self.stream_reader:
            self.stream_reader.release()

        self._publish_status("STOPPED")

        logger.info("Cleanup completed")


def main():
    """메인 함수"""
    logger.info("=" * 50)
    logger.info("PPE Detector Component Starting")
    logger.info("=" * 50)

    component = PPEDetectorComponent()

    try:
        component.initialize()
        component.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("PPE Detector Component Stopped")


if __name__ == "__main__":
    main()
