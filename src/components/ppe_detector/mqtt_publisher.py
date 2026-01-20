#!/usr/bin/env python3
"""
MQTT Publisher
AWS IoT Core로 메시지를 발행하는 모듈
Greengrass IPC와 직접 MQTT 연결 모두 지원
"""

import json
import logging
import os
import time
from threading import Lock
from typing import Dict, Any, Optional

logger = logging.getLogger('MQTTPublisher')

# Greengrass IPC 클라이언트
GREENGRASS_IPC_AVAILABLE = False
try:
    import awsiot.greengrasscoreipc as ipc
    from awsiot.greengrasscoreipc.model import (
        PublishToIoTCoreRequest,
        PublishToTopicRequest,
        PublishMessage,
        JsonMessage,
        BinaryMessage,
        QOS
    )
    GREENGRASS_IPC_AVAILABLE = True
    logger.info("Greengrass IPC available")
except ImportError:
    logger.warning("Greengrass IPC not available")

# AWS IoT SDK (직접 연결용)
AWS_IOT_SDK_AVAILABLE = False
try:
    from awscrt import mqtt
    from awsiot import mqtt_connection_builder
    AWS_IOT_SDK_AVAILABLE = True
    logger.info("AWS IoT SDK available")
except ImportError:
    logger.warning("AWS IoT SDK not available")


class MQTTPublisher:
    """MQTT 메시지 퍼블리셔"""

    def __init__(
        self,
        thing_name: str = None,
        use_greengrass_ipc: bool = True,
        # 직접 연결용 옵션
        endpoint: str = None,
        cert_path: str = None,
        key_path: str = None,
        ca_path: str = None,
        client_id: str = None
    ):
        """
        Args:
            thing_name: AWS IoT Thing 이름
            use_greengrass_ipc: Greengrass IPC 사용 여부
            endpoint: AWS IoT 엔드포인트 (직접 연결용)
            cert_path: 인증서 경로 (직접 연결용)
            key_path: 프라이빗 키 경로 (직접 연결용)
            ca_path: CA 인증서 경로 (직접 연결용)
            client_id: MQTT 클라이언트 ID (직접 연결용)
        """
        self.thing_name = thing_name or os.environ.get('AWS_IOT_THING_NAME', 'unknown')
        self.use_greengrass_ipc = use_greengrass_ipc and GREENGRASS_IPC_AVAILABLE

        self.lock = Lock()
        self.ipc_client = None
        self.mqtt_connection = None

        # 통계
        self.stats = {
            'messages_published': 0,
            'messages_failed': 0,
            'bytes_sent': 0
        }

        # Greengrass IPC 또는 직접 MQTT 연결 초기화
        if self.use_greengrass_ipc:
            self._init_greengrass_ipc()
        elif endpoint and cert_path and key_path:
            self._init_direct_mqtt(endpoint, cert_path, key_path, ca_path, client_id)
        else:
            logger.warning("No MQTT backend available. Messages will be logged only.")

    def _init_greengrass_ipc(self):
        """Greengrass IPC 클라이언트 초기화"""
        try:
            self.ipc_client = ipc.connect()
            logger.info("Greengrass IPC client connected")
        except Exception as e:
            logger.error(f"Failed to connect Greengrass IPC: {e}")
            self.use_greengrass_ipc = False

    def _init_direct_mqtt(
        self,
        endpoint: str,
        cert_path: str,
        key_path: str,
        ca_path: str = None,
        client_id: str = None
    ):
        """직접 MQTT 연결 초기화"""
        if not AWS_IOT_SDK_AVAILABLE:
            logger.error("AWS IoT SDK not available for direct connection")
            return

        try:
            # 기본 CA 경로
            if ca_path is None:
                ca_path = '/greengrass/v2/rootCA.pem'

            # 클라이언트 ID
            if client_id is None:
                client_id = f"{self.thing_name}-publisher-{int(time.time())}"

            # MQTT 연결 빌드
            self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
                endpoint=endpoint,
                cert_filepath=cert_path,
                pri_key_filepath=key_path,
                ca_filepath=ca_path,
                client_id=client_id,
                clean_session=False,
                keep_alive_secs=30
            )

            # 연결
            connect_future = self.mqtt_connection.connect()
            connect_future.result(timeout=10)

            logger.info(f"Direct MQTT connected to {endpoint}")

        except Exception as e:
            logger.error(f"Failed to connect direct MQTT: {e}")
            self.mqtt_connection = None

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        qos: int = 1
    ) -> bool:
        """
        메시지 발행

        Args:
            topic: MQTT 토픽
            payload: 메시지 페이로드 (딕셔너리)
            qos: QoS 레벨 (0, 1)

        Returns:
            bool: 발행 성공 여부
        """
        try:
            # 페이로드를 JSON 문자열로 변환
            message_json = json.dumps(payload, ensure_ascii=False)
            message_bytes = message_json.encode('utf-8')

            with self.lock:
                if self.use_greengrass_ipc and self.ipc_client:
                    success = self._publish_via_ipc(topic, message_json, qos)
                elif self.mqtt_connection:
                    success = self._publish_via_direct(topic, message_json, qos)
                else:
                    # 백엔드 없음 - 로그만 출력
                    logger.info(f"[DRY RUN] Topic: {topic}, Payload: {message_json[:200]}...")
                    success = True

            if success:
                self.stats['messages_published'] += 1
                self.stats['bytes_sent'] += len(message_bytes)
                logger.debug(f"Published to {topic}: {len(message_bytes)} bytes")
            else:
                self.stats['messages_failed'] += 1

            return success

        except Exception as e:
            logger.error(f"Publish error: {e}")
            self.stats['messages_failed'] += 1
            return False

    def _publish_via_ipc(self, topic: str, message: str, qos: int) -> bool:
        """Greengrass IPC를 통한 발행"""
        try:
            # IoT Core로 발행
            request = PublishToIoTCoreRequest(
                topic_name=topic,
                qos=QOS.AT_LEAST_ONCE if qos >= 1 else QOS.AT_MOST_ONCE,
                payload=message.encode('utf-8')
            )

            operation = self.ipc_client.new_publish_to_iot_core()
            operation.activate(request)
            future_response = operation.get_response()
            future_response.result(timeout=10)

            return True

        except Exception as e:
            logger.error(f"IPC publish error: {e}")
            return False

    def _publish_via_direct(self, topic: str, message: str, qos: int) -> bool:
        """직접 MQTT 연결을 통한 발행"""
        try:
            # QoS 매핑
            mqtt_qos = mqtt.QoS.AT_LEAST_ONCE if qos >= 1 else mqtt.QoS.AT_MOST_ONCE

            # 발행
            publish_future, packet_id = self.mqtt_connection.publish(
                topic=topic,
                payload=message,
                qos=mqtt_qos
            )

            # 결과 대기
            publish_future.result(timeout=10)

            return True

        except Exception as e:
            logger.error(f"Direct MQTT publish error: {e}")
            return False

    def publish_local(
        self,
        topic: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        로컬 Greengrass 토픽에 발행 (디바이스 간 통신)

        Args:
            topic: 로컬 토픽
            payload: 메시지 페이로드

        Returns:
            bool: 발행 성공 여부
        """
        if not self.use_greengrass_ipc or not self.ipc_client:
            logger.warning("Local publish requires Greengrass IPC")
            return False

        try:
            message_json = json.dumps(payload, ensure_ascii=False)

            request = PublishToTopicRequest(
                topic=topic,
                publish_message=PublishMessage(
                    json_message=JsonMessage(message=payload)
                )
            )

            operation = self.ipc_client.new_publish_to_topic()
            operation.activate(request)
            future_response = operation.get_response()
            future_response.result(timeout=5)

            self.stats['messages_published'] += 1
            logger.debug(f"Published locally to {topic}")

            return True

        except Exception as e:
            logger.error(f"Local publish error: {e}")
            self.stats['messages_failed'] += 1
            return False

    def disconnect(self):
        """연결 종료"""
        try:
            if self.mqtt_connection:
                disconnect_future = self.mqtt_connection.disconnect()
                disconnect_future.result(timeout=10)
                logger.info("MQTT disconnected")

        except Exception as e:
            logger.error(f"Disconnect error: {e}")

    def get_stats(self) -> Dict:
        """통계 반환"""
        return self.stats.copy()


class MockMQTTPublisher(MQTTPublisher):
    """테스트용 Mock MQTT 퍼블리셔"""

    def __init__(self, **kwargs):
        self.published_messages = []
        self.stats = {
            'messages_published': 0,
            'messages_failed': 0,
            'bytes_sent': 0
        }
        self.thing_name = kwargs.get('thing_name', 'test-device')

    def publish(self, topic: str, payload: Dict[str, Any], qos: int = 1) -> bool:
        """메시지를 리스트에 저장"""
        message = {
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'timestamp': time.time()
        }
        self.published_messages.append(message)
        self.stats['messages_published'] += 1
        self.stats['bytes_sent'] += len(json.dumps(payload))

        logger.info(f"[MOCK] Published to {topic}: {json.dumps(payload)[:100]}...")
        return True

    def get_messages(self) -> list:
        """발행된 메시지 목록 반환"""
        return self.published_messages.copy()

    def clear_messages(self):
        """메시지 목록 초기화"""
        self.published_messages.clear()


# 테스트 코드
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='MQTT Publisher Test')
    parser.add_argument('--topic', type=str, default='ppe/test',
                        help='MQTT topic')
    parser.add_argument('--message', type=str, default='Hello from PPE Detector',
                        help='Test message')
    parser.add_argument('--mock', action='store_true',
                        help='Use mock publisher')
    args = parser.parse_args()

    # 퍼블리셔 생성
    if args.mock:
        publisher = MockMQTTPublisher(thing_name='test-device')
    else:
        publisher = MQTTPublisher(
            thing_name='RaspberryPi5-PPE',
            use_greengrass_ipc=True
        )

    # 테스트 메시지 발행
    test_payload = {
        'message': args.message,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'device': 'test'
    }

    success = publisher.publish(args.topic, test_payload)
    print(f"Publish result: {'Success' if success else 'Failed'}")
    print(f"Stats: {publisher.get_stats()}")

    if args.mock:
        print(f"Published messages: {publisher.get_messages()}")
