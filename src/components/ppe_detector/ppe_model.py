#!/usr/bin/env python3
"""
PPE Detection Model
YOLOv8을 사용한 개인보호장비(PPE) 인식 모듈
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional

import cv2
import numpy as np

logger = logging.getLogger('PPEDetector')

# PPE 클래스 정의
PPE_CLASSES = {
    0: 'person',
    1: 'hardhat',        # 안전모
    2: 'no_hardhat',     # 안전모 미착용
    3: 'safety_vest',    # 안전 조끼
    4: 'no_safety_vest', # 안전 조끼 미착용
    5: 'safety_glasses', # 보안경
    6: 'gloves',         # 장갑
    7: 'mask',           # 마스크
}

# PPE 클래스 색상 (BGR)
PPE_COLORS = {
    'person': (255, 128, 0),       # 주황
    'hardhat': (0, 255, 0),        # 녹색 (착용)
    'no_hardhat': (0, 0, 255),     # 빨강 (미착용)
    'safety_vest': (0, 255, 0),    # 녹색
    'no_safety_vest': (0, 0, 255), # 빨강
    'safety_glasses': (255, 255, 0), # 노랑
    'gloves': (255, 0, 255),       # 자홍
    'mask': (128, 255, 128),       # 연두
}


class PPEDetector:
    """YOLOv8 기반 PPE 인식기"""

    def __init__(
        self,
        model_path: str = None,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = 'cpu',
        classes: Dict[int, str] = None
    ):
        """
        Args:
            model_path: YOLOv8 모델 파일 경로 (.pt)
            confidence_threshold: 최소 신뢰도 임계값
            iou_threshold: NMS IoU 임계값
            device: 추론 장치 ('cpu', 'cuda', 'cuda:0')
            classes: 클래스 ID -> 이름 매핑 딕셔너리
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.classes = classes or PPE_CLASSES

        self.model = None
        self._load_model()

    def _load_model(self):
        """모델 로드"""
        try:
            from ultralytics import YOLO

            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"Loading custom model: {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                # 기본 YOLOv8n 모델 사용 (PPE 전용 모델이 없을 경우)
                logger.warning(f"Model not found at {self.model_path}, using default yolov8n")
                self.model = YOLO('yolov8n.pt')

            # 디바이스 설정
            if self.device.startswith('cuda'):
                import torch
                if torch.cuda.is_available():
                    self.model.to(self.device)
                    logger.info(f"Using CUDA device: {self.device}")
                else:
                    logger.warning("CUDA not available, falling back to CPU")
                    self.device = 'cpu'
            else:
                logger.info("Using CPU for inference")

            # 워밍업 (첫 추론 속도 향상)
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model.predict(dummy_input, verbose=False)

            logger.info("Model loaded successfully")

        except ImportError:
            logger.error("ultralytics package not installed. Run: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        프레임에서 PPE 감지 수행

        Args:
            frame: BGR 형식의 이미지 (numpy array)

        Returns:
            List[Dict]: 감지 결과 목록
                [
                    {
                        'class': 'hardhat',
                        'class_id': 1,
                        'confidence': 0.85,
                        'bbox': [x1, y1, x2, y2]
                    },
                    ...
                ]
        """
        if self.model is None:
            logger.error("Model not loaded")
            return []

        try:
            # YOLOv8 추론
            results = self.model.predict(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False
            )

            detections = []

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for i in range(len(boxes)):
                    # 바운딩 박스
                    bbox = boxes.xyxy[i].cpu().numpy().tolist()
                    bbox = [int(x) for x in bbox]

                    # 클래스 ID
                    class_id = int(boxes.cls[i].cpu().numpy())

                    # 신뢰도
                    confidence = float(boxes.conf[i].cpu().numpy())

                    # 클래스 이름 (커스텀 모델의 경우)
                    if class_id in self.classes:
                        class_name = self.classes[class_id]
                    else:
                        # 기본 YOLOv8 클래스 (COCO)
                        class_name = result.names.get(class_id, f'class_{class_id}')

                    detections.append({
                        'class': class_name,
                        'class_id': class_id,
                        'confidence': round(confidence, 3),
                        'bbox': bbox
                    })

            return detections

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []

    def detect_and_draw(self, frame: np.ndarray) -> tuple:
        """
        감지 수행 및 결과를 이미지에 그리기

        Args:
            frame: BGR 형식의 이미지

        Returns:
            tuple: (감지 결과 리스트, 결과가 그려진 이미지)
        """
        detections = self.detect(frame)
        result_frame = self.draw_detections(frame, detections)
        return detections, result_frame

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        감지 결과를 이미지에 그리기

        Args:
            frame: 원본 이미지
            detections: 감지 결과 리스트
            show_confidence: 신뢰도 표시 여부

        Returns:
            np.ndarray: 결과가 그려진 이미지
        """
        result_frame = frame.copy()

        for det in detections:
            class_name = det['class']
            confidence = det['confidence']
            x1, y1, x2, y2 = det['bbox']

            # 색상 선택
            color = PPE_COLORS.get(class_name, (128, 128, 128))

            # 바운딩 박스 그리기
            thickness = 2
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, thickness)

            # 라벨 텍스트
            if show_confidence:
                label = f"{class_name}: {confidence:.2f}"
            else:
                label = class_name

            # 텍스트 배경
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 1
            (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, font_thickness)

            cv2.rectangle(
                result_frame,
                (x1, y1 - text_height - 10),
                (x1 + text_width + 10, y1),
                color,
                -1  # 채우기
            )

            # 텍스트
            cv2.putText(
                result_frame,
                label,
                (x1 + 5, y1 - 5),
                font,
                font_scale,
                (255, 255, 255),  # 흰색 텍스트
                font_thickness
            )

        return result_frame

    def get_summary(self, detections: List[Dict]) -> Dict:
        """
        감지 결과 요약

        Args:
            detections: 감지 결과 리스트

        Returns:
            Dict: 클래스별 개수
        """
        summary = {}
        for det in detections:
            class_name = det['class']
            summary[class_name] = summary.get(class_name, 0) + 1
        return summary


class PPEComplianceChecker:
    """PPE 착용 규정 준수 검사기"""

    def __init__(
        self,
        required_ppe: List[str] = None,
        detector: PPEDetector = None
    ):
        """
        Args:
            required_ppe: 필수 PPE 목록 (예: ['hardhat', 'safety_vest'])
            detector: PPEDetector 인스턴스
        """
        self.required_ppe = required_ppe or ['hardhat', 'safety_vest']
        self.detector = detector

    def check_compliance(self, detections: List[Dict]) -> Dict:
        """
        PPE 착용 규정 준수 확인

        Args:
            detections: 감지 결과 리스트

        Returns:
            Dict: 규정 준수 결과
        """
        # 감지된 사람 수
        persons = [d for d in detections if d['class'] == 'person']

        # 감지된 PPE 종류
        detected_ppe = set(d['class'] for d in detections
                          if d['class'] in self.required_ppe)

        # 미착용 PPE
        missing_ppe = set(self.required_ppe) - detected_ppe

        # "no_" prefix가 붙은 클래스 확인 (명시적 미착용)
        explicit_violations = [d for d in detections
                               if d['class'].startswith('no_')]

        result = {
            'compliant': len(missing_ppe) == 0 and len(explicit_violations) == 0,
            'persons_detected': len(persons),
            'detected_ppe': list(detected_ppe),
            'missing_ppe': list(missing_ppe),
            'violations': [d['class'] for d in explicit_violations],
            'summary': {
                'total_persons': len(persons),
                'compliant_count': len(persons) - len(explicit_violations),
                'violation_count': len(explicit_violations)
            }
        }

        return result


# 테스트 코드
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='PPE Detector Test')
    parser.add_argument('--image', type=str, help='Test image path')
    parser.add_argument('--video', type=str, help='Test video path')
    parser.add_argument('--camera', type=int, default=0, help='Camera index')
    parser.add_argument('--model', type=str, default=None, help='Model path')
    parser.add_argument('--conf', type=float, default=0.5, help='Confidence threshold')
    args = parser.parse_args()

    # 모델 초기화
    detector = PPEDetector(
        model_path=args.model,
        confidence_threshold=args.conf
    )

    if args.image:
        # 이미지 테스트
        img = cv2.imread(args.image)
        detections, result_img = detector.detect_and_draw(img)

        print(f"Detections: {detections}")
        print(f"Summary: {detector.get_summary(detections)}")

        cv2.imshow('PPE Detection Result', result_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    elif args.video or args.camera is not None:
        # 비디오/카메라 테스트
        source = args.video if args.video else args.camera
        cap = cv2.VideoCapture(source)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            detections, result_frame = detector.detect_and_draw(frame)

            # FPS 표시
            summary = detector.get_summary(detections)
            cv2.putText(result_frame, f"Objects: {summary}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow('PPE Detection', result_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
