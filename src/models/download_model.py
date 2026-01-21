#!/usr/bin/env python3
"""
PPE 모델 다운로드 및 ONNX 변환 스크립트

이 스크립트는 두 가지 방식으로 실행할 수 있습니다:

1. 개발 PC에서 실행 (PyTorch 설치된 환경):
   - YOLOv8 모델을 다운로드하고 ONNX로 변환
   - pip install ultralytics 필요

2. 라즈베리파이에서 실행 (PyTorch 없는 환경):
   - 사전 변환된 ONNX 모델을 GitHub에서 다운로드
   - 추가 의존성 없음
"""

import os
import sys
import argparse
import urllib.request
import shutil
from pathlib import Path

# 사전 변환된 ONNX 모델 URL (GitHub Releases 등에서 호스팅)
ONNX_MODEL_URLS = {
    'yolov8n': 'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx',
    'yolov8s': 'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.onnx',
    'yolov8m': 'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.onnx',
}


def download_onnx_direct(model_name: str, output_dir: str) -> str:
    """
    사전 변환된 ONNX 모델을 직접 다운로드 (PyTorch 불필요)

    Args:
        model_name: 모델 이름 (yolov8n, yolov8s, yolov8m)
        output_dir: 저장 디렉토리

    Returns:
        저장된 모델 경로
    """
    if model_name not in ONNX_MODEL_URLS:
        print(f"오류: '{model_name}'에 대한 사전 변환된 ONNX 모델이 없습니다.")
        print(f"사용 가능한 모델: {list(ONNX_MODEL_URLS.keys())}")
        return None

    url = ONNX_MODEL_URLS[model_name]
    output_path = Path(output_dir) / f"{model_name}.onnx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"ONNX 모델 다운로드 중: {model_name}")
    print(f"URL: {url}")
    print(f"저장 경로: {output_path}")

    try:
        # 진행 표시와 함께 다운로드
        def show_progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, block_num * block_size * 100 // total_size)
                mb_downloaded = block_num * block_size / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r다운로드 중: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='', flush=True)

        urllib.request.urlretrieve(url, output_path, show_progress)
        print()  # 줄바꿈

        # 파일 크기 확인
        file_size = os.path.getsize(output_path)
        print(f"다운로드 완료: {file_size / (1024*1024):.2f} MB")

        return str(output_path)

    except Exception as e:
        print(f"\n다운로드 오류: {e}")
        print("\n대안:")
        print("  1. 개발 PC에서 --convert 옵션으로 직접 변환")
        print("  2. 수동으로 ONNX 모델 다운로드 후 복사")
        return None


def convert_to_onnx(model_name: str, output_dir: str, input_size: int = 640) -> str:
    """
    YOLOv8 모델을 다운로드하고 ONNX로 변환 (개발 PC에서 실행)

    Args:
        model_name: 모델 이름 (yolov8n, yolov8s, yolov8m 등)
        output_dir: 저장 디렉토리
        input_size: 입력 이미지 크기

    Returns:
        저장된 ONNX 모델 경로
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("=" * 50)
        print("오류: ultralytics 패키지가 설치되지 않았습니다.")
        print("=" * 50)
        print("")
        print("이 기능은 개발 PC에서만 사용할 수 있습니다.")
        print("")
        print("옵션 1: 개발 PC에서 ultralytics 설치 후 변환")
        print("  pip install ultralytics")
        print("  python3 download_model.py --model yolov8n --convert")
        print("")
        print("옵션 2: 사전 변환된 ONNX 모델 직접 다운로드")
        print("  python3 download_model.py --model yolov8n")
        print("")
        return None

    print(f"YOLOv8 모델 다운로드 중: {model_name}")

    # 모델 다운로드
    model = YOLO(f"{model_name}.pt")

    # 출력 경로
    output_path = Path(output_dir) / f"{model_name}.onnx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"ONNX로 변환 중... (입력 크기: {input_size}x{input_size})")

    # ONNX 내보내기
    model.export(
        format='onnx',
        imgsz=input_size,
        simplify=True,  # ONNX 그래프 단순화
        opset=12,       # ONNX opset 버전 (OpenCV DNN 호환성)
        dynamic=False,  # 고정 입력 크기 (추론 최적화)
    )

    # 내보낸 파일 이동
    exported_path = Path(f"{model_name}.onnx")
    if exported_path.exists():
        shutil.move(str(exported_path), str(output_path))
        print(f"ONNX 모델 저장됨: {output_path}")

        # 파일 크기
        file_size = os.path.getsize(output_path)
        print(f"모델 크기: {file_size / (1024*1024):.2f} MB")

        return str(output_path)
    else:
        # ultralytics가 다른 위치에 저장했을 수 있음
        print(f"변환된 파일을 찾을 수 없습니다. 현재 디렉토리를 확인하세요.")
        return None


def verify_onnx_model(model_path: str) -> bool:
    """
    ONNX 모델 검증 (OpenCV DNN으로 로드 테스트)

    Args:
        model_path: ONNX 모델 경로

    Returns:
        검증 성공 여부
    """
    import cv2
    import numpy as np

    if not os.path.exists(model_path):
        print(f"오류: 모델 파일이 없습니다: {model_path}")
        return False

    file_size = os.path.getsize(model_path)
    print(f"모델 파일 크기: {file_size / (1024*1024):.2f} MB")

    try:
        print("OpenCV DNN으로 모델 로드 중...")
        net = cv2.dnn.readNetFromONNX(model_path)

        # 테스트 추론
        print("테스트 추론 실행 중...")
        dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
        blob = cv2.dnn.blobFromImage(dummy_input, 1/255.0, (640, 640), swapRB=True)
        net.setInput(blob)
        output = net.forward()

        print(f"출력 형태: {output.shape}")
        print("모델 검증 성공!")
        return True

    except Exception as e:
        print(f"모델 검증 오류: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='PPE 인식 ONNX 모델 다운로드/변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 라즈베리파이: 사전 변환된 ONNX 모델 다운로드
  python3 download_model.py --model yolov8n

  # 개발 PC: PyTorch 모델을 ONNX로 변환
  python3 download_model.py --model yolov8n --convert

  # 모델 검증
  python3 download_model.py --model yolov8n --verify
        """
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='yolov8n',
        choices=['yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x'],
        help='다운로드할 모델 (기본: yolov8n, 라즈베리파이 권장)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./models',
        help='모델 저장 디렉토리 (기본: ./models)'
    )
    parser.add_argument(
        '--convert', '-c',
        action='store_true',
        help='PyTorch 모델을 ONNX로 변환 (ultralytics 필요, 개발 PC용)'
    )
    parser.add_argument(
        '--verify', '-v',
        action='store_true',
        help='다운로드 후 OpenCV DNN으로 모델 검증'
    )
    parser.add_argument(
        '--size', '-s',
        type=int,
        default=640,
        help='입력 이미지 크기 (기본: 640)'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  PPE 인식 ONNX 모델 다운로드")
    print("=" * 50)
    print("")
    print(f"모델: {args.model}")
    print(f"저장 경로: {args.output}")
    print(f"모드: {'변환 (개발 PC)' if args.convert else '직접 다운로드'}")
    print("")

    # 출력 디렉토리 생성
    os.makedirs(args.output, exist_ok=True)

    # 모델 다운로드/변환
    if args.convert:
        # 개발 PC: ultralytics로 변환
        model_path = convert_to_onnx(args.model, args.output, args.size)
    else:
        # 라즈베리파이: 사전 변환된 ONNX 직접 다운로드
        model_path = download_onnx_direct(args.model, args.output)

    if model_path is None:
        print("\n모델 다운로드/변환 실패")
        sys.exit(1)

    # 검증
    if args.verify:
        print("")
        print("-" * 50)
        print("모델 검증")
        print("-" * 50)
        if not verify_onnx_model(model_path):
            sys.exit(1)

    print("")
    print("=" * 50)
    print("  완료!")
    print("=" * 50)
    print("")
    print(f"ONNX 모델 경로: {model_path}")
    print("")
    print("다음 단계:")
    print("  1. 모델 파일을 라즈베리파이로 복사 (scp 사용)")
    print(f"     scp {model_path} pi@raspberrypi:/opt/ppe-detector/models/")
    print("")
    print("  2. 또는 config.yaml에서 model.path 설정:")
    print(f"     model_path: \"{model_path}\"")
    print("")
    print("  3. 테스트 실행:")
    print(f"     python3 ppe_model.py --camera 0 --model {model_path}")


if __name__ == "__main__":
    main()
