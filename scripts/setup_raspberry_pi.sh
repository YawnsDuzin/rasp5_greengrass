#!/bin/bash
#
# 라즈베리파이5 초기 설정 스크립트
# PPE 인식 시스템을 위한 환경 설정
#

set -e

echo "========================================"
echo "  라즈베리파이5 PPE 인식 환경 설정"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 루트 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    echo "사용법: sudo $0"
    exit 1
fi

# 1. 시스템 업데이트
log_info "시스템 패키지 업데이트 중..."
apt update
apt upgrade -y

# 2. 필수 패키지 설치
log_info "필수 패키지 설치 중..."
apt install -y \
    git \
    curl \
    wget \
    unzip \
    vim \
    htop \
    python3 \
    python3-pip \
    python3-venv \
    default-jdk

# 3. OpenCV 의존성 설치
log_info "OpenCV 의존성 설치 중..."
apt install -y \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libhdf5-dev \
    libharfbuzz-dev \
    libwebp-dev \
    libtiff-dev \
    libilmbase-dev \
    libopenexr-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad

# 4. Greengrass 사용자/그룹 생성
log_info "Greengrass 사용자 및 그룹 생성 중..."
if ! id "ggc_user" &>/dev/null; then
    useradd --system --create-home ggc_user
fi

if ! getent group ggc_group &>/dev/null; then
    groupadd --system ggc_group
fi

usermod -a -G ggc_group ggc_user

# 5. sysctl 설정
log_info "시스템 보안 설정 중..."
cat > /etc/sysctl.d/99-greengrass.conf << EOF
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF

sysctl -p /etc/sysctl.d/99-greengrass.conf

# 6. cgroup 설정
log_info "cgroup 설정 확인 중..."
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if [ -f "$CMDLINE_FILE" ]; then
    if ! grep -q "cgroup_enable=memory" "$CMDLINE_FILE"; then
        log_warn "cgroup 설정을 cmdline.txt에 추가합니다..."
        # 기존 내용을 한 줄로 읽고 추가
        CURRENT=$(cat "$CMDLINE_FILE" | tr -d '\n')
        echo "${CURRENT} cgroup_enable=memory cgroup_memory=1 systemd.unified_cgroup_hierarchy=0" > "$CMDLINE_FILE"
        log_warn "재부팅 후 cgroup 설정이 적용됩니다."
    else
        log_info "cgroup 설정이 이미 존재합니다."
    fi
else
    log_warn "cmdline.txt 파일을 찾을 수 없습니다. 수동으로 cgroup 설정을 추가하세요."
fi

# 7. PPE Detector 디렉토리 생성
log_info "PPE Detector 디렉토리 생성 중..."
mkdir -p /opt/ppe-detector/models
mkdir -p /opt/ppe-detector/logs

# 현재 사용자에게 권한 부여 (sudo로 실행한 경우 SUDO_USER 사용)
ACTUAL_USER=${SUDO_USER:-$USER}
chown -R $ACTUAL_USER:$ACTUAL_USER /opt/ppe-detector

# 8. Python 가상 환경 생성
log_info "Python 가상 환경 생성 중..."
sudo -u $ACTUAL_USER python3 -m venv /opt/ppe-detector/venv

# 9. 환경 변수 설정
log_info "환경 변수 설정 중..."
cat > /etc/profile.d/ppe-detector.sh << 'EOF'
export PPE_DETECTOR_VENV=/opt/ppe-detector/venv
export PPE_DETECTOR_PATH=/opt/ppe-detector
export JAVA_HOME=/usr/lib/jvm/default-java
EOF

# 10. Java 버전 확인
log_info "Java 버전 확인..."
java -version

# 11. Python 버전 확인
log_info "Python 버전 확인..."
python3 --version

# 12. 버전 정보 출력
echo ""
echo "========================================"
echo "  설치 완료"
echo "========================================"
echo ""
log_info "설치된 버전:"
echo "  - Java: $(java -version 2>&1 | head -1)"
echo "  - Python: $(python3 --version)"
echo "  - OpenCV: $(python3 -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo 'Not installed yet')"
echo ""
log_info "생성된 디렉토리:"
echo "  - /opt/ppe-detector"
echo "  - /opt/ppe-detector/venv"
echo "  - /opt/ppe-detector/models"
echo ""

# 재부팅 필요 여부 확인
if ! grep -q "cgroup_enable=memory" /proc/cmdline; then
    log_warn "cgroup 설정을 적용하려면 재부팅이 필요합니다."
    echo ""
    read -p "지금 재부팅하시겠습니까? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "재부팅 중..."
        reboot
    else
        log_warn "나중에 수동으로 재부팅하세요: sudo reboot"
    fi
else
    log_info "모든 설정이 완료되었습니다!"
fi

echo ""
echo "다음 단계: Greengrass 설치 스크립트 실행"
echo "  ./scripts/install_greengrass.sh"
