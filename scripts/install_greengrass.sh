#!/bin/bash
#
# AWS IoT Greengrass V2 설치 스크립트
# 라즈베리파이5용
#

set -e

echo "========================================"
echo "  AWS IoT Greengrass V2 설치"
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

# 설정 변수 (사용자 입력 또는 기본값)
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
THING_NAME="${THING_NAME:-RaspberryPi5-PPE}"
THING_GROUP="${THING_GROUP:-PPEDetectorGroup}"
GREENGRASS_ROOT="/greengrass/v2"

# 루트 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    echo "사용법: sudo -E $0"
    echo ""
    echo "AWS 자격 증명이 설정된 상태에서 실행하세요:"
    echo "  export AWS_ACCESS_KEY_ID=AKIA..."
    echo "  export AWS_SECRET_ACCESS_KEY=..."
    echo "  export AWS_DEFAULT_REGION=ap-northeast-2"
    exit 1
fi

# AWS 자격 증명 확인
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    log_error "AWS 자격 증명이 설정되지 않았습니다."
    echo ""
    echo "다음 환경 변수를 설정한 후 다시 실행하세요:"
    echo "  export AWS_ACCESS_KEY_ID=AKIA..."
    echo "  export AWS_SECRET_ACCESS_KEY=..."
    echo "  export AWS_DEFAULT_REGION=ap-northeast-2"
    echo ""
    echo "그 다음: sudo -E $0"
    exit 1
fi

# 사용자 입력 받기
echo ""
log_input "AWS 리전 [$AWS_REGION]: "
read -r input
AWS_REGION=${input:-$AWS_REGION}

log_input "Thing 이름 [$THING_NAME]: "
read -r input
THING_NAME=${input:-$THING_NAME}

log_input "Thing 그룹 [$THING_GROUP]: "
read -r input
THING_GROUP=${input:-$THING_GROUP}

echo ""
echo "========================================"
echo "  설정 확인"
echo "========================================"
echo "  AWS 리전: $AWS_REGION"
echo "  Thing 이름: $THING_NAME"
echo "  Thing 그룹: $THING_GROUP"
echo "  설치 경로: $GREENGRASS_ROOT"
echo "========================================"
echo ""

read -p "계속 진행하시겠습니까? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "설치가 취소되었습니다."
    exit 0
fi

# 작업 디렉토리 생성
log_info "작업 디렉토리 생성 중..."
WORK_DIR="/tmp/greengrass-setup"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Greengrass Nucleus 다운로드
log_info "Greengrass Nucleus 다운로드 중..."
if [ ! -f "greengrass-nucleus-latest.zip" ]; then
    curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip \
        -o greengrass-nucleus-latest.zip
fi

# 압축 해제
log_info "압축 해제 중..."
rm -rf GreengrassInstaller
unzip -q greengrass-nucleus-latest.zip -d GreengrassInstaller

# 기존 설치 확인
if [ -d "$GREENGRASS_ROOT" ]; then
    log_warn "기존 Greengrass 설치가 발견되었습니다: $GREENGRASS_ROOT"
    read -p "기존 설치를 삭제하고 다시 설치하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "기존 설치 중지 및 삭제 중..."
        systemctl stop greengrass 2>/dev/null || true
        rm -rf "$GREENGRASS_ROOT"
    else
        log_error "설치가 취소되었습니다."
        exit 1
    fi
fi

# Greengrass 설치
log_info "Greengrass V2 설치 중..."
log_info "이 과정은 몇 분 정도 소요됩니다..."

java -Droot="$GREENGRASS_ROOT" -Dlog.store=FILE \
    -jar ./GreengrassInstaller/lib/Greengrass.jar \
    --aws-region "$AWS_REGION" \
    --thing-name "$THING_NAME" \
    --thing-group-name "$THING_GROUP" \
    --thing-policy-name "GreengrassV2IoTThingPolicy" \
    --tes-role-name "GreengrassV2TokenExchangeRole" \
    --tes-role-alias-name "GreengrassCoreTokenExchangeRoleAlias" \
    --component-default-user ggc_user:ggc_group \
    --provision true \
    --setup-system-service true

# 설치 확인
log_info "설치 확인 중..."
sleep 5

if systemctl is-active --quiet greengrass; then
    log_info "Greengrass 서비스가 정상적으로 실행 중입니다!"
else
    log_warn "Greengrass 서비스 상태 확인 중..."
    systemctl status greengrass --no-pager || true
fi

# 정리
log_info "임시 파일 정리 중..."
cd /
rm -rf "$WORK_DIR"

# 결과 출력
echo ""
echo "========================================"
echo "  설치 완료"
echo "========================================"
echo ""
log_info "Greengrass가 성공적으로 설치되었습니다!"
echo ""
echo "  Thing 이름: $THING_NAME"
echo "  설치 경로: $GREENGRASS_ROOT"
echo "  로그 경로: $GREENGRASS_ROOT/logs"
echo ""
echo "유용한 명령어:"
echo "  # 서비스 상태 확인"
echo "  sudo systemctl status greengrass"
echo ""
echo "  # 컴포넌트 목록"
echo "  sudo $GREENGRASS_ROOT/bin/greengrass-cli component list"
echo ""
echo "  # 로그 확인"
echo "  sudo tail -f $GREENGRASS_ROOT/logs/greengrass.log"
echo ""
echo "다음 단계: PPE 인식 컴포넌트 배포"
echo "  ./scripts/deploy_component.sh"
