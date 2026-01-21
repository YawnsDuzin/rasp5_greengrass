#!/bin/bash
#
# PPE Detector 컴포넌트 배포 스크립트
#

set -e

echo "========================================"
echo "  PPE Detector 컴포넌트 배포"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_input() { echo -e "${BLUE}[INPUT]${NC} $1"; }

# 설정 변수
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPONENT_NAME="com.example.PPEDetector"
COMPONENT_VERSION="1.0.0"

# 설정 파일 로드
CONFIG_FILE="$PROJECT_ROOT/configs/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    log_info "설정 파일 로드: $CONFIG_FILE"
    # YAML 파싱 (간단한 버전)
    AWS_REGION=$(grep 'aws_region:' "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
    S3_BUCKET=$(grep 's3_bucket:' "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
    THING_NAME=$(grep 'thing_name:' "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
fi

# 기본값 설정
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
S3_BUCKET="${S3_BUCKET:-}"
THING_NAME="${THING_NAME:-RaspberryPi5-PPE}"

# 사용자 입력
echo ""
log_input "배포 모드를 선택하세요:"
echo "  1) 로컬 배포 (Greengrass CLI 사용)"
echo "  2) 클라우드 배포 (AWS CLI 사용)"
echo ""
read -p "선택 [1]: " -r MODE
MODE=${MODE:-1}

case $MODE in
    1)
        # 로컬 배포
        log_info "로컬 배포를 시작합니다..."

        # 아티팩트 준비
        BUILD_DIR="$PROJECT_ROOT/build"
        mkdir -p "$BUILD_DIR"

        log_info "아티팩트 패키징 중..."
        rm -rf "$BUILD_DIR/ppe-detector"
        mkdir -p "$BUILD_DIR/ppe-detector"

        # 소스 코드 복사
        cp -r "$PROJECT_ROOT/src/components/ppe_detector/"* "$BUILD_DIR/ppe-detector/"

        # 모델 파일 복사 (ONNX 형식)
        mkdir -p "$BUILD_DIR/ppe-detector/models"
        if [ -f "$PROJECT_ROOT/models/yolov8n.onnx" ]; then
            cp "$PROJECT_ROOT/models/yolov8n.onnx" "$BUILD_DIR/ppe-detector/models/"
        else
            log_warn "ONNX 모델 파일이 없습니다. src/models/download_model.py를 실행하세요."
        fi

        # 로컬 레시피 생성 (파일 경로 사용)
        LOCAL_RECIPE="$BUILD_DIR/recipe.yaml"
        cat > "$LOCAL_RECIPE" << EOF
---
RecipeFormatVersion: "2020-01-25"
ComponentName: $COMPONENT_NAME
ComponentVersion: "$COMPONENT_VERSION"
ComponentDescription: PPE Detection Component (Local Deployment)
ComponentPublisher: Local

Manifests:
  - Platform:
      os: linux
      architecture: aarch64
    Lifecycle:
      Install:
        RequiresPrivilege: false
        Timeout: 300
        Script: |
          #!/bin/bash
          set -e
          VENV_PATH="{artifacts:path}/venv"
          if [ ! -d "\$VENV_PATH" ]; then
            python3 -m venv "\$VENV_PATH"
          fi
          source "\$VENV_PATH/bin/activate"
          pip install --upgrade pip
          pip install -r "{artifacts:path}/requirements.txt"
      Run:
        RequiresPrivilege: false
        Script: |
          #!/bin/bash
          source "{artifacts:path}/venv/bin/activate"
          export MODEL_PATH="{artifacts:path}/models/yolov8n.onnx"
          python3 "{artifacts:path}/main.py"
    Artifacts:
      - Uri: file://$BUILD_DIR/ppe-detector
        Permission:
          Read: OWNER
          Execute: OWNER

ComponentConfiguration:
  DefaultConfiguration:
    rtspUrl: "rtsp://admin:password@192.168.1.100:554/stream"
    confidenceThreshold: "0.5"
    alertTopic: "ppe/alerts"
    statusTopic: "ppe/status"
    requiredPpe: "hardhat,safety_vest"
EOF

        log_info "Greengrass CLI로 로컬 배포 중..."

        # Greengrass CLI 경로
        GG_CLI="/greengrass/v2/bin/greengrass-cli"

        if [ ! -f "$GG_CLI" ]; then
            log_error "Greengrass CLI를 찾을 수 없습니다: $GG_CLI"
            log_warn "먼저 aws.greengrass.Cli 컴포넌트를 배포하세요."
            exit 1
        fi

        # 로컬 배포 실행
        sudo "$GG_CLI" deployment create \
            --recipeDir "$BUILD_DIR" \
            --artifactDir "$BUILD_DIR" \
            --merge "$COMPONENT_NAME=$COMPONENT_VERSION"

        log_info "배포 요청 완료!"

        # 상태 확인
        sleep 5
        log_info "컴포넌트 상태 확인..."
        sudo "$GG_CLI" component list
        ;;

    2)
        # 클라우드 배포
        log_info "클라우드 배포를 시작합니다..."

        if [ -z "$S3_BUCKET" ]; then
            log_input "S3 버킷 이름: "
            read -r S3_BUCKET
        fi

        log_input "Thing 이름 [$THING_NAME]: "
        read -r input
        THING_NAME=${input:-$THING_NAME}

        # 아티팩트 패키징
        BUILD_DIR="$PROJECT_ROOT/build"
        mkdir -p "$BUILD_DIR"

        log_info "아티팩트 패키징 중..."
        rm -rf "$BUILD_DIR/ppe-detector"
        mkdir -p "$BUILD_DIR/ppe-detector"
        cp -r "$PROJECT_ROOT/src/components/ppe_detector/"* "$BUILD_DIR/ppe-detector/"

        # ZIP 생성
        cd "$BUILD_DIR"
        rm -f ppe-detector.zip
        zip -r ppe-detector.zip ppe-detector/

        # S3 업로드
        log_info "S3에 업로드 중..."
        S3_PATH="s3://$S3_BUCKET/components/$COMPONENT_NAME/$COMPONENT_VERSION/ppe-detector.zip"
        aws s3 cp ppe-detector.zip "$S3_PATH" --region "$AWS_REGION"

        # 레시피 업데이트
        CLOUD_RECIPE="$BUILD_DIR/recipe-cloud.yaml"
        sed "s|s3://YOUR_BUCKET_NAME|s3://$S3_BUCKET|g" \
            "$PROJECT_ROOT/configs/recipe.yaml" > "$CLOUD_RECIPE"

        # 컴포넌트 등록
        log_info "컴포넌트 등록 중..."
        aws greengrassv2 create-component-version \
            --inline-recipe "fileb://$CLOUD_RECIPE" \
            --region "$AWS_REGION"

        # 배포 생성
        log_info "배포 생성 중..."

        # Thing ARN 가져오기
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        THING_ARN="arn:aws:iot:$AWS_REGION:$ACCOUNT_ID:thing/$THING_NAME"

        aws greengrassv2 create-deployment \
            --target-arn "$THING_ARN" \
            --deployment-name "PPE-Detector-Deployment-$(date +%Y%m%d%H%M%S)" \
            --components "{\"$COMPONENT_NAME\":{\"componentVersion\":\"$COMPONENT_VERSION\"}}" \
            --region "$AWS_REGION"

        log_info "클라우드 배포 요청 완료!"
        ;;

    *)
        log_error "잘못된 선택입니다."
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "  배포 완료"
echo "========================================"
echo ""
echo "상태 확인 명령어:"
echo "  sudo /greengrass/v2/bin/greengrass-cli component list"
echo ""
echo "로그 확인:"
echo "  sudo tail -f /greengrass/v2/logs/$COMPONENT_NAME.log"
