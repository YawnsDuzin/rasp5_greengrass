#!/usr/bin/env python3
"""
PPE Detection Model - OpenCV DNN + ONNX 버전
PyTorch 없이 OpenCV DNN 백엔드를 사용하여 ONNX 모델로 추론
라즈베리파이 Bookworm OS (Python 3.11) 호환
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger('PPEDetector')

# PPE 클래스 정의 (PPE 전용 모델용)
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

# COCO 클래스 (기본 YOLOv8 모델용 - 80개 클래스 중 일부)
COCO_CLASSES = {
    0: 'person',
    # ... 나머지 COCO 클래스들
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
    """OpenCV DNN 기반 ONNX 모델 PPE 인식기"""

    def __init__(
        self,
        model_path: str = None,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        classes: Dict[int, str] = None,
        use_cuda: bool = False
    ):
        """
        Args:
            model_path: ONNX 모델 파일 경로 (.onnx)
            confidence_threshold: 최소 신뢰도 임계값
            iou_threshold: NMS IoU 임계값
            input_size: 모델 입력 크기 (width, height)
            classes: 클래스 ID -> 이름 매핑 딕셔너리
            use_cuda: CUDA 백엔드 사용 여부 (라즈베리파이에서는 False)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.classes = classes or PPE_CLASSES
        self.use_cuda = use_cuda

        self.net = None
        self.output_layers = None
        self._load_model()

    def _load_model(self):
        """ONNX 모델 로드"""
        try:
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"Loading ONNX model: {self.model_path}")
            else:
                # 기본 모델 경로 시도
                default_paths = [
                    '/opt/ppe-detector/models/yolov8n.onnx',
                    './models/yolov8n.onnx',
                    'yolov8n.onnx'
                ]
                for path in default_paths:
                    if os.path.exists(path):
                        self.model_path = path
                        break

                if not self.model_path or not os.path.exists(self.model_path):
                    raise FileNotFoundError(
                        f"ONNX 모델을 찾을 수 없습니다. "
                        f"모델 경로: {self.model_path}\n"
                        f"모델 다운로드: python3 src/models/download_model.py --model yolov8n"
                    )

            # OpenCV DNN으로 ONNX 모델 로드
            self.net = cv2.dnn.readNetFromONNX(self.model_path)

            # 백엔드 설정
            if self.use_cuda and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                logger.info("Using CUDA backend")
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            else:
                logger.info("Using CPU backend")
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

            # 출력 레이어 이름 가져오기
            self.output_layers = self.net.getUnconnectedOutLayersNames()

            # 워밍업 (첫 추론 속도 향상)
            logger.info("Warming up model...")
            dummy_input = np.zeros((self.input_size[1], self.input_size[0], 3), dtype=np.uint8)
            self._inference(dummy_input)

            logger.info(f"Model loaded successfully: {self.model_path}")
            logger.info(f"Input size: {self.input_size}")
            logger.info(f"Classes: {len(self.classes)}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float, int, int]:
        """
        이미지 전처리 (YOLOv8 형식)

        Args:
            frame: BGR 형식의 원본 이미지

        Returns:
            blob: 모델 입력용 blob
            x_factor, y_factor: 좌표 변환을 위한 스케일 팩터
            pad_w, pad_h: 패딩 크기
        """
        img_h, img_w = frame.shape[:2]
        input_w, input_h = self.input_size

        # 비율 유지하며 리사이즈
        scale = min(input_w / img_w, input_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 패딩 (letterbox)
        pad_w = (input_w - new_w) // 2
        pad_h = (input_h - new_h) // 2

        padded = np.full((input_h, input_w, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h + new_h, pad_w:pad_w + new_w] = resized

        # BGR -> RGB, HWC -> CHW, normalize
        blob = cv2.dnn.blobFromImage(
            padded,
            scalefactor=1/255.0,
            size=(input_w, input_h),
            mean=(0, 0, 0),
            swapRB=True,
            crop=False
        )

        # 좌표 변환을 위한 팩터
        x_factor = img_w / (new_w)
        y_factor = img_h / (new_h)

        return blob, x_factor, y_factor, pad_w, pad_h, scale

    def _inference(self, frame: np.ndarray) -> np.ndarray:
        """
        모델 추론 실행

        Args:
            frame: 원본 이미지

        Returns:
            outputs: 모델 출력
        """
        blob, x_factor, y_factor, pad_w, pad_h, scale = self._preprocess(frame)
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        return outputs, x_factor, y_factor, pad_w, pad_h, scale

    def _postprocess(
        self,
        outputs: np.ndarray,
        x_factor: float,
        y_factor: float,
        pad_w: int,
        pad_h: int,
        scale: float,
        img_w: int,
        img_h: int
    ) -> List[Dict]:
        """
        모델 출력 후처리 (YOLOv8 형식)

        YOLOv8 출력 형식: [1, 84, 8400] 또는 [1, num_classes+4, num_detections]
        - 84 = 4 (bbox) + 80 (classes) for COCO
        - 각 열이 하나의 detection

        Args:
            outputs: 모델 출력
            x_factor, y_factor: 좌표 스케일 팩터
            pad_w, pad_h: 패딩 크기
            scale: 리사이즈 스케일
            img_w, img_h: 원본 이미지 크기

        Returns:
            List[Dict]: 감지 결과
        """
        detections = []

        # YOLOv8 출력 처리
        output = outputs[0]

        # 출력 형태 확인 및 변환
        if len(output.shape) == 3:
            output = output[0]  # batch 차원 제거

        # YOLOv8: [84, 8400] -> [8400, 84] 전치
        if output.shape[0] < output.shape[1]:
            output = output.T

        num_detections = output.shape[0]
        num_classes = output.shape[1] - 4  # bbox 4개 제외

        boxes = []
        confidences = []
        class_ids = []

        for i in range(num_detections):
            # 클래스별 점수
            class_scores = output[i, 4:]

            # 최대 점수와 클래스 ID
            max_score = np.max(class_scores)
            class_id = np.argmax(class_scores)

            if max_score < self.confidence_threshold:
                continue

            # 바운딩 박스 (cx, cy, w, h) -> (x1, y1, x2, y2)
            cx, cy, w, h = output[i, :4]

            # 패딩 제거 및 원본 좌표로 변환
            x1 = int(((cx - w/2) - pad_w) / scale)
            y1 = int(((cy - h/2) - pad_h) / scale)
            x2 = int(((cx + w/2) - pad_w) / scale)
            y2 = int(((cy + h/2) - pad_h) / scale)

            # 경계 체크
            x1 = max(0, min(x1, img_w))
            y1 = max(0, min(y1, img_h))
            x2 = max(0, min(x2, img_w))
            y2 = max(0, min(y2, img_h))

            # NMS용 데이터 저장
            boxes.append([x1, y1, x2 - x1, y2 - y1])  # x, y, w, h 형식
            confidences.append(float(max_score))
            class_ids.append(int(class_id))

        # Non-Maximum Suppression
        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes(
                boxes,
                confidences,
                self.confidence_threshold,
                self.iou_threshold
            )

            # OpenCV 버전에 따른 indices 처리
            if len(indices) > 0:
                if isinstance(indices, np.ndarray):
                    indices = indices.flatten()
                else:
                    indices = [i[0] if isinstance(i, (list, tuple)) else i for i in indices]

                for i in indices:
                    x, y, w, h = boxes[i]
                    class_id = class_ids[i]

                    # 클래스 이름
                    if class_id in self.classes:
                        class_name = self.classes[class_id]
                    else:
                        class_name = f'class_{class_id}'

                    detections.append({
                        'class': class_name,
                        'class_id': class_id,
                        'confidence': round(confidences[i], 3),
                        'bbox': [x, y, x + w, y + h]  # x1, y1, x2, y2 형식
                    })

        return detections

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        프레임에서 PPE 감지 수행

        Args:
            frame: BGR 형식의 이미지 (numpy array)

        Returns:
            List[Dict]: 감지 결과 목록
        """
        if self.net is None:
            logger.error("Model not loaded")
            return []

        try:
            img_h, img_w = frame.shape[:2]

            # 추론
            outputs, x_factor, y_factor, pad_w, pad_h, scale = self._inference(frame)

            # 후처리
            detections = self._postprocess(
                outputs, x_factor, y_factor, pad_w, pad_h, scale, img_w, img_h
            )

            return detections

        except Exception as e:
            logger.error(f"Detection error: {e}")
            import traceback
            traceback.print_exc()
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
    import time

    parser = argparse.ArgumentParser(description='PPE Detector Test (OpenCV DNN + ONNX)')
    parser.add_argument('--image', type=str, help='Test image path')
    parser.add_argument('--video', type=str, help='Test video path')
    parser.add_argument('--camera', type=int, default=None, help='Camera index')
    parser.add_argument('--model', type=str, default='yolov8n.onnx', help='ONNX model path')
    parser.add_argument('--conf', type=float, default=0.5, help='Confidence threshold')
    parser.add_argument('--size', type=int, default=640, help='Input size')
    args = parser.parse_args()

    print("=" * 50)
    print("PPE Detector - OpenCV DNN + ONNX")
    print("=" * 50)

    # 모델 초기화
    try:
        detector = PPEDetector(
            model_path=args.model,
            confidence_threshold=args.conf,
            input_size=(args.size, args.size)
        )
    except FileNotFoundError as e:
        print(f"\n오류: {e}")
        print("\n모델 다운로드 방법:")
        print("  python3 src/models/download_model.py --model yolov8n")
        exit(1)

    if args.image:
        # 이미지 테스트
        img = cv2.imread(args.image)
        if img is None:
            print(f"이미지를 읽을 수 없습니다: {args.image}")
            exit(1)

        start = time.time()
        detections, result_img = detector.detect_and_draw(img)
        elapsed = time.time() - start

        print(f"\n추론 시간: {elapsed*1000:.1f}ms")
        print(f"감지 결과: {detections}")
        print(f"요약: {detector.get_summary(detections)}")

        cv2.imshow('PPE Detection Result', result_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    elif args.video or args.camera is not None:
        # 비디오/카메라 테스트
        source = args.video if args.video else args.camera
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            print(f"비디오 소스를 열 수 없습니다: {source}")
            exit(1)

        frame_count = 0
        total_time = 0

        print("\n실시간 감지 시작... (q를 눌러 종료)")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            start = time.time()
            detections, result_frame = detector.detect_and_draw(frame)
            elapsed = time.time() - start

            frame_count += 1
            total_time += elapsed

            # FPS 및 정보 표시
            fps = 1 / elapsed if elapsed > 0 else 0
            avg_fps = frame_count / total_time if total_time > 0 else 0

            info = f"FPS: {fps:.1f} (Avg: {avg_fps:.1f}) | Objects: {len(detections)}"
            cv2.putText(result_frame, info, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow('PPE Detection (OpenCV DNN)', result_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        print(f"\n평균 FPS: {avg_fps:.1f}")
        print(f"총 프레임: {frame_count}")

    else:
        print("\n사용법:")
        print("  이미지 테스트: python3 ppe_model.py --image test.jpg --model yolov8n.onnx")
        print("  카메라 테스트: python3 ppe_model.py --camera 0 --model yolov8n.onnx")
        print("  비디오 테스트: python3 ppe_model.py --video test.mp4 --model yolov8n.onnx")
