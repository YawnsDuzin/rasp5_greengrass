#!/usr/bin/env python3
"""
PPE 모델 다운로드 스크립트
기본 YOLOv8 모델 또는 PPE 전용 모델을 다운로드합니다.
"""

import os
import sys
import argparse
from pathlib import Path


def download_yolov8_model(model_name: str, output_dir: str):
    """
    YOLOv8 기본 모델 다운로드

    Args:
        model_name: 모델 이름 (yolov8n, yolov8s, yolov8m 등)
        output_dir: 저장 디렉토리
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics 패키지가 필요합니다.")
        print("설치: pip install ultralytics")
        sys.exit(1)

    print(f"YOLOv8 모델 다운로드 중: {model_name}")

    # 모델 다운로드
    model = YOLO(f"{model_name}.pt")

    # 출력 경로
    output_path = Path(output_dir) / f"{model_name}.pt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 모델 저장
    # YOLOv8은 자동으로 ~/.cache/ultralytics/에 다운로드됨
    # 원하는 위치로 복사
    import shutil
    cache_path = Path.home() / ".cache" / "ultralytics" / f"{model_name}.pt"

    if cache_path.exists():
        shutil.copy(cache_path, output_path)
        print(f"모델 저장됨: {output_path}")
    else:
        # 직접 export
        model.export(format='pt')
        print(f"모델이 기본 캐시 위치에 저장됨")

    return str(output_path)


def download_ppe_model(output_dir: str):
    """
    PPE 전용 모델 다운로드 (예시)

    실제로는 Roboflow, HuggingFace 등에서 다운로드하거나
    직접 훈련한 모델을 사용합니다.
    """
    print("PPE 전용 모델 다운로드...")
    print("")
    print("PPE 전용 모델 옵션:")
    print("1. Roboflow Universe에서 PPE Detection 모델 검색")
    print("   https://universe.roboflow.com/search?q=ppe+detection")
    print("")
    print("2. Kaggle에서 PPE 데이터셋으로 직접 훈련")
    print("   https://www.kaggle.com/search?q=ppe+detection")
    print("")
    print("3. 기본 YOLOv8n 모델 사용 (person 클래스만 감지)")
    print("   기본 모델을 다운로드하려면: --model yolov8n")
    print("")

    # 기본 모델 다운로드 제안
    response = input("기본 YOLOv8n 모델을 다운로드하시겠습니까? (y/n): ")
    if response.lower() == 'y':
        return download_yolov8_model('yolov8n', output_dir)

    return None


def verify_model(model_path: str):
    """모델 파일 검증"""
    if not os.path.exists(model_path):
        print(f"오류: 모델 파일이 없습니다: {model_path}")
        return False

    file_size = os.path.getsize(model_path)
    print(f"모델 파일 크기: {file_size / 1024 / 1024:.2f} MB")

    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        print(f"모델 클래스: {model.names}")
        print("모델 검증 성공!")
        return True
    except Exception as e:
        print(f"모델 로드 오류: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='PPE 인식 모델 다운로드')
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='yolov8n',
        choices=['yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x', 'ppe'],
        help='다운로드할 모델 (기본: yolov8n)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='/opt/ppe-detector/models',
        help='모델 저장 디렉토리'
    )
    parser.add_argument(
        '--verify', '-v',
        action='store_true',
        help='다운로드 후 모델 검증'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  PPE 인식 모델 다운로드")
    print("=" * 50)
    print("")

    # 출력 디렉토리 생성
    os.makedirs(args.output, exist_ok=True)

    # 모델 다운로드
    if args.model == 'ppe':
        model_path = download_ppe_model(args.output)
    else:
        model_path = download_yolov8_model(args.model, args.output)

    # 검증
    if args.verify and model_path:
        print("")
        print("모델 검증 중...")
        verify_model(model_path)

    print("")
    print("완료!")
    if model_path:
        print(f"모델 경로: {model_path}")
        print("")
        print("다음 단계:")
        print("  1. config.yaml에서 model.path 설정 확인")
        print("  2. 컴포넌트 배포: ./scripts/deploy_component.sh")


if __name__ == "__main__":
    main()
