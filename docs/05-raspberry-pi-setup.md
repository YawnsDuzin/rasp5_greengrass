# 05. 라즈베리파이5 환경 설정

이 문서에서는 라즈베리파이5에 운영 체제를 설치하고, AWS IoT Greengrass V2를 설치하여 AWS 클라우드와 연결합니다.

## 목차
1. [하드웨어 준비](#1-하드웨어-준비)
2. [Raspberry Pi OS 설치](#2-raspberry-pi-os-설치)
3. [기본 시스템 설정](#3-기본-시스템-설정)
4. [Greengrass 사전 요구 사항 설치](#4-greengrass-사전-요구-사항-설치)
5. [AWS IoT Greengrass V2 설치](#5-aws-iot-greengrass-v2-설치)
6. [Greengrass 설치 확인](#6-greengrass-설치-확인)
7. [PPE 인식 환경 설정](#7-ppe-인식-환경-설정)

---

## 1. 하드웨어 준비

### 1.1 필요 장비

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       필요 하드웨어 체크리스트                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ☐ 라즈베리파이5 (4GB 또는 8GB RAM)                                     │
│      └─ 8GB 권장 (ML 모델 실행에 유리)                                  │
│                                                                         │
│  ☐ microSD 카드 (64GB 이상, Class 10 / U3)                             │
│      └─ 고속 카드 권장 (읽기 속도 100MB/s 이상)                         │
│                                                                         │
│  ☐ USB-C 전원 어댑터 (5V 5A, 27W)                                      │
│      └─ 공식 어댑터 권장, 저전력 시 불안정                               │
│                                                                         │
│  ☐ microSD 카드 리더 (PC용)                                            │
│                                                                         │
│  ☐ 이더넷 케이블 또는 WiFi                                              │
│      └─ 초기 설정은 이더넷 권장                                         │
│                                                                         │
│  ☐ IP 카메라 (RTSP 지원)                                               │
│      └─ 테스트용: USB 웹캠도 가능                                       │
│                                                                         │
│  (선택) 모니터, 키보드, 마우스                                          │
│      └─ SSH 사용 시 불필요                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 라즈베리파이5 핀 배치 (참고)

```
                    라즈베리파이5 상단 뷰
    ┌─────────────────────────────────────────────────┐
    │  ▣ USB-C     ▣ micro HDMI x2    ▣ 3.5mm Audio │
    │                                                 │
    │  ┌─────────────────────────────────────────┐   │
    │  │ ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●│   │
    │  │ ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●│   │
    │  └─────────────────────────────────────────┘   │
    │              GPIO 40핀 헤더                     │
    │                                                 │
    │  ┌───┐  ┌───┐                                  │
    │  │USB│  │USB│  ← USB 3.0 포트                  │
    │  │ 3 │  │ 3 │                                  │
    │  └───┘  └───┘                                  │
    │  ┌───┐  ┌───┐                                  │
    │  │USB│  │USB│  ← USB 2.0 포트                  │
    │  │ 2 │  │ 2 │                                  │
    │  └───┘  └───┘                                  │
    │                              ┌────┐            │
    │                              │ 이더│            │
    │                              │ 넷  │            │
    │                              └────┘            │
    └─────────────────────────────────────────────────┘
```

---

## 2. Raspberry Pi OS 설치

### 2.1 Raspberry Pi Imager 다운로드

공식 이미지 작성 도구를 사용합니다.

1. https://www.raspberrypi.com/software/ 접속
2. 운영 체제에 맞는 Raspberry Pi Imager 다운로드
3. 설치 후 실행

### 2.2 OS 이미지 굽기

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Raspberry Pi Imager                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. [디바이스 선택]                                                     │
│     └─ Raspberry Pi 5 선택                                             │
│                                                                         │
│  2. [운영체제 선택]                                                     │
│     └─ Raspberry Pi OS (64-bit)                                        │
│        └─ 반드시 64-bit 선택! (arm64)                                  │
│        └─ Desktop 버전 또는 Lite 버전                                  │
│           · Desktop: GUI 포함 (모니터 연결 시)                          │
│           · Lite: CLI만 (SSH 사용 시, 권장)                            │
│                                                                         │
│  3. [저장소 선택]                                                       │
│     └─ microSD 카드 선택                                               │
│                                                                         │
│  4. [⚙️ 설정] (오른쪽 하단 톱니바퀴)                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 고급 설정 (⚙️ 설정)

톱니바퀴 아이콘을 클릭하여 사전 설정을 구성합니다:

```
┌─────────────────────────────────────────────────────────────┐
│                      고급 옵션                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ☑ 호스트 이름: [raspberrypi5-ppe    ].local               │
│                                                             │
│  ☑ SSH 활성화                                               │
│    (●) 비밀번호 인증 사용                                   │
│                                                             │
│  ☑ 사용자 이름 및 비밀번호 설정                              │
│    사용자 이름: [pi                   ]                     │
│    비밀번호:   [********             ]                     │
│                                                             │
│  ☑ WiFi 설정 (선택사항)                                     │
│    SSID:     [YourWiFiName           ]                     │
│    비밀번호: [YourWiFiPassword        ]                     │
│    국가:     [KR                      ]                     │
│                                                             │
│  ☑ 로케일 설정                                              │
│    시간대:   [Asia/Seoul              ]                     │
│    키보드:   [us                      ]                     │
│                                                             │
│  [저장]                                                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 이미지 쓰기

1. **"쓰기"** 버튼 클릭
2. 경고 확인 후 **"예"**
3. 완료까지 대기 (약 5-15분)

### 2.5 첫 부팅

1. microSD 카드를 라즈베리파이에 삽입
2. 이더넷 케이블 연결 (또는 WiFi 설정된 경우 불필요)
3. 전원 연결
4. 약 1-2분 대기 (첫 부팅 시 초기화)

---

## 3. 기본 시스템 설정

### 3.1 SSH 접속

터미널(맥/리눅스) 또는 PowerShell(윈도우)에서:

```bash
# 호스트 이름으로 접속
ssh pi@raspberrypi5-ppe.local

# 또는 IP 주소로 접속 (IP는 공유기 관리 페이지에서 확인)
ssh pi@192.168.1.xxx
```

처음 접속 시:
```
The authenticity of host 'raspberrypi5-ppe.local' can't be established.
ED25519 key fingerprint is SHA256:xxxxx.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
```

**yes** 입력 후 비밀번호 입력

### 3.2 시스템 업데이트

```bash
# 패키지 목록 업데이트
sudo apt update

# 시스템 업그레이드
sudo apt upgrade -y

# 재부팅 (커널 업데이트 적용)
sudo reboot
```

### 3.3 필수 패키지 설치

```bash
# 기본 개발 도구
sudo apt install -y \
    git \
    curl \
    wget \
    unzip \
    vim \
    htop

# Python 관련
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv

# Java (Greengrass Nucleus 실행에 필요)
sudo apt install -y default-jdk

# 버전 확인
java -version
# openjdk version "17.0.x" ...

python3 --version
# Python 3.11.x
```

### 3.4 시스템 설정

```bash
# raspi-config로 추가 설정
sudo raspi-config
```

```
┌─────────────────────────────────────────────────────────────┐
│                   Raspberry Pi Configuration                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1 System Options     → S1 Hostname 확인/변경              │
│  2 Display Options                                          │
│  3 Interface Options  → I2 SSH 활성화 확인                  │
│                       → I6 Serial Port (필요 시)           │
│  4 Performance        → P2 GPU Memory: 128 → 256 변경     │
│                          (영상 처리 성능 향상)              │
│  5 Localisation       → L2 Timezone: Asia/Seoul           │
│  6 Advanced Options   → A1 Expand Filesystem              │
│                          (SD 카드 전체 사용)               │
│                                                             │
│  <Select>    <Finish>                                       │
└─────────────────────────────────────────────────────────────┘
```

변경 후 재부팅:
```bash
sudo reboot
```

---

## 4. Greengrass 사전 요구 사항 설치

### 4.1 시스템 사용자 생성

Greengrass 컴포넌트가 실행될 시스템 사용자를 생성합니다:

```bash
# ggc_user 사용자 및 ggc_group 그룹 생성
sudo useradd --system --create-home ggc_user
sudo groupadd --system ggc_group
sudo usermod -a -G ggc_group ggc_user

# 확인
id ggc_user
# uid=xxx(ggc_user) gid=xxx(ggc_user) groups=xxx(ggc_user),xxx(ggc_group)
```

### 4.2 하드링크/소프트링크 보호 설정

```bash
# sysctl 설정 확인 및 수정
sudo nano /etc/sysctl.d/99-greengrass.conf
```

다음 내용 입력:
```
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
```

설정 적용:
```bash
sudo sysctl -p /etc/sysctl.d/99-greengrass.conf
```

### 4.3 cgroup 설정 (메모리/CPU 제한용)

```bash
# cmdline.txt 수정
sudo nano /boot/firmware/cmdline.txt
```

기존 내용 **끝에** 다음 추가 (한 줄로, 줄바꿈 없이):
```
cgroup_enable=memory cgroup_memory=1 systemd.unified_cgroup_hierarchy=0
```

예시 (전체 한 줄):
```
console=serial0,115200 console=tty1 root=PARTUUID=xxx rootfstype=ext4 ... cgroup_enable=memory cgroup_memory=1 systemd.unified_cgroup_hierarchy=0
```

재부팅:
```bash
sudo reboot
```

### 4.4 사전 요구 사항 확인 스크립트

```bash
# Greengrass 체커 스크립트 다운로드
curl -O https://raw.githubusercontent.com/aws-greengrass/aws-greengrass-nucleus/main/gg-device-setup/check_ggc_dependencies.sh

# 실행 권한 부여
chmod +x check_ggc_dependencies.sh

# 의존성 체크 실행
sudo ./check_ggc_dependencies.sh
```

예상 출력:
```
========================Checking kernel configuration========================
...
CONFIG_CGROUPS: Enabled
CONFIG_CGROUP_DEVICE: Enabled
CONFIG_MEMCG: Enabled
...
========================Checking commands========================
Java: found
Python: found
...
========================Summary========================
All required checks passed!
```

---

## 5. AWS IoT Greengrass V2 설치

### 5.1 AWS 자격 증명 설정

먼저 개발 PC에서 생성한 AWS 액세스 키를 라즈베리파이에 설정합니다:

```bash
# AWS CLI 설치
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 설치 확인
aws --version

# AWS 자격 증명 설정
aws configure
```

```
AWS Access Key ID [None]: AKIA...YOUR_ACCESS_KEY
AWS Secret Access Key [None]: YOUR_SECRET_KEY
Default region name [None]: ap-northeast-2
Default output format [None]: json
```

### 5.2 Greengrass Nucleus 다운로드

```bash
# 작업 디렉토리 생성
mkdir -p ~/greengrass-setup && cd ~/greengrass-setup

# Greengrass Nucleus 다운로드
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip \
    -o greengrass-nucleus-latest.zip

# 압축 해제
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller

# 확인
ls GreengrassInstaller/
# lib/  LICENSE  NOTICE  README.md  THIRD-PARTY-LICENSES  bin/
```

### 5.3 Greengrass 설치 실행

```bash
# 환경 변수 설정 (실제 값으로 변경!)
export AWS_REGION="ap-northeast-2"
export THING_NAME="RaspberryPi5-PPE"
export THING_GROUP="PPEDetectorGroup"

# Greengrass 설치 실행
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
    -jar ./GreengrassInstaller/lib/Greengrass.jar \
    --aws-region $AWS_REGION \
    --thing-name $THING_NAME \
    --thing-group-name $THING_GROUP \
    --thing-policy-name GreengrassV2IoTThingPolicy \
    --tes-role-name GreengrassV2TokenExchangeRole \
    --tes-role-alias-name GreengrassCoreTokenExchangeRoleAlias \
    --component-default-user ggc_user:ggc_group \
    --provision true \
    --setup-system-service true
```

### 5.4 설치 과정 설명

```
설치 실행 시 자동으로 수행되는 작업:

┌─────────────────────────────────────────────────────────────────────────┐
│  1. AWS IoT에 Thing 생성 (또는 기존 Thing 사용)                         │
│     └─ RaspberryPi5-PPE                                                │
│                                                                         │
│  2. Thing Group 생성 (또는 기존 그룹 사용)                              │
│     └─ PPEDetectorGroup                                                │
│                                                                         │
│  3. IoT 인증서 생성 및 다운로드                                         │
│     └─ /greengrass/v2/thingCert.crt                                   │
│     └─ /greengrass/v2/privKey.key                                     │
│     └─ /greengrass/v2/rootCA.pem                                      │
│                                                                         │
│  4. IAM 역할 생성 (Token Exchange Role)                                │
│     └─ GreengrassV2TokenExchangeRole                                  │
│                                                                         │
│  5. IoT 역할 별칭 생성                                                  │
│     └─ GreengrassCoreTokenExchangeRoleAlias                           │
│                                                                         │
│  6. Greengrass Nucleus 설치                                            │
│     └─ /greengrass/v2/                                                │
│                                                                         │
│  7. systemd 서비스 등록                                                │
│     └─ greengrass.service                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.5 예상 출력

```
Provisioning AWS IoT resources for the device with IoT Thing Name: [RaspberryPi5-PPE]...
Creating new IoT Thing Policy: [GreengrassV2IoTThingPolicy]...
Creating keys and certificate...
Attaching policy to certificate...
Creating IoT Thing "RaspberryPi5-PPE"...
Attaching certificate to IoT Thing...
Creating Thing Group: [PPEDetectorGroup]...
Adding IoT Thing "RaspberryPi5-PPE" to group "PPEDetectorGroup"...
Setting up Greengrass Nucleus as a system service...
Launching Greengrass Nucleus...
Greengrass Nucleus is running.
Successfully set up Greengrass Nucleus as a system service!
```

---

## 6. Greengrass 설치 확인

### 6.1 서비스 상태 확인

```bash
# Greengrass 서비스 상태 확인
sudo systemctl status greengrass

# 예상 출력:
# ● greengrass.service - Greengrass Core
#    Loaded: loaded (/etc/systemd/system/greengrass.service; enabled)
#    Active: active (running) since ...
```

### 6.2 Greengrass CLI 설치

```bash
# Greengrass CLI 배포 (AWS 콘솔에서 하거나 아래 명령 사용)
sudo /greengrass/v2/bin/greengrass-cli component list
```

CLI가 없으면 AWS 콘솔에서 배포:
1. IoT Greengrass → 배포 → 배포 생성
2. 대상: RaspberryPi5-PPE
3. 컴포넌트 추가: `aws.greengrass.Cli`
4. 배포

### 6.3 로그 확인

```bash
# Greengrass 코어 로그
sudo tail -f /greengrass/v2/logs/greengrass.log

# 특정 컴포넌트 로그 (나중에 PPE Detector 배포 후)
sudo tail -f /greengrass/v2/logs/com.example.PPEDetector.log
```

### 6.4 AWS 콘솔에서 확인

1. **AWS IoT Greengrass** 콘솔 접속
2. **코어 디바이스** 메뉴
3. `RaspberryPi5-PPE` 확인

```
┌─────────────────────────────────────────────────────────────┐
│                    코어 디바이스 상세                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  이름: RaspberryPi5-PPE                                    │
│  상태: ● 정상 (Healthy)                                    │
│                                                             │
│  마지막 상태 업데이트: 방금 전                               │
│                                                             │
│  설치된 컴포넌트:                                            │
│  - aws.greengrass.Nucleus (2.12.x)                         │
│  - aws.greengrass.Cli (2.12.x)                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. PPE 인식 환경 설정

### 7.1 Python 가상 환경 생성

```bash
# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/ppe-detector
sudo chown pi:pi /opt/ppe-detector
cd /opt/ppe-detector

# Python 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

### 7.2 OpenCV 설치

라즈베리파이에서 OpenCV 설치:

```bash
# 시스템 의존성 설치
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libhdf5-dev \
    libharfbuzz-dev \
    libwebp-dev \
    libtiff5-dev \
    libjasper-dev \
    libilmbase-dev \
    libopenexr-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgstreamer1.0-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad

# 가상 환경에서 OpenCV 설치
source /opt/ppe-detector/venv/bin/activate
pip install opencv-python-headless
```

### 7.3 PyTorch 및 YOLOv8 설치

```bash
# 가상 환경 활성화 (이미 되어있으면 스킵)
source /opt/ppe-detector/venv/bin/activate

# PyTorch 설치 (라즈베리파이5 arm64용)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Ultralytics (YOLOv8)
pip install ultralytics

# AWS IoT SDK
pip install awsiotsdk

# 기타 의존성
pip install numpy pillow pyyaml
```

### 7.4 설치 확인

```bash
source /opt/ppe-detector/venv/bin/activate

python3 << 'EOF'
import cv2
import torch
from ultralytics import YOLO

print(f"OpenCV version: {cv2.__version__}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print("All dependencies installed successfully!")
EOF
```

예상 출력:
```
OpenCV version: 4.x.x
PyTorch version: 2.x.x
CUDA available: False
All dependencies installed successfully!
```

### 7.5 RTSP 스트림 테스트

```bash
# IP 카메라 RTSP 스트림 테스트
python3 << 'EOF'
import cv2

# RTSP URL을 실제 카메라 주소로 변경
rtsp_url = "rtsp://admin:password@192.168.1.100:554/stream1"

cap = cv2.VideoCapture(rtsp_url)
if cap.isOpened():
    print("RTSP connection successful!")
    ret, frame = cap.read()
    if ret:
        print(f"Frame size: {frame.shape}")
    cap.release()
else:
    print("Failed to connect to RTSP stream")
EOF
```

### 7.6 시스템 시작 시 자동 설정

가상 환경 경로를 Greengrass 컴포넌트에서 사용할 수 있도록 설정:

```bash
# 환경 변수 파일 생성
sudo nano /etc/profile.d/ppe-detector.sh
```

내용:
```bash
export PPE_DETECTOR_VENV=/opt/ppe-detector/venv
export PPE_DETECTOR_PATH=/opt/ppe-detector
```

```bash
# 적용
source /etc/profile.d/ppe-detector.sh
```

---

## 요약

이 문서에서 완료한 작업:

| 단계 | 내용 |
|------|------|
| OS 설치 | Raspberry Pi OS 64-bit |
| 시스템 설정 | SSH, 업데이트, Java 설치 |
| Greengrass 준비 | 사용자 생성, cgroup 설정 |
| Greengrass 설치 | 자동 프로비저닝으로 설치 |
| PPE 환경 | Python, OpenCV, PyTorch, YOLOv8 |

---

## 다음 단계

라즈베리파이5 환경 설정이 완료되었습니다!

다음 문서에서는 **PPE 인식 컴포넌트를 개발**합니다.

➡️ [06. PPE 인식 컴포넌트 개발](06-component-development.md)

---

## 체크리스트

- [ ] Raspberry Pi OS 설치 완료
- [ ] SSH 접속 성공
- [ ] 시스템 업데이트 완료
- [ ] Java 설치 완료
- [ ] Greengrass 사전 요구 사항 설치
- [ ] Greengrass V2 설치 완료
- [ ] AWS 콘솔에서 디바이스 확인
- [ ] Python 환경 설정 완료
- [ ] OpenCV, PyTorch, YOLOv8 설치

---

## 문제 해결

### Greengrass 설치 실패 시

```bash
# 로그 확인
sudo cat /greengrass/v2/logs/greengrass.log | tail -100

# 재설치 (기존 삭제 후)
sudo systemctl stop greengrass
sudo rm -rf /greengrass/v2
# 5.3 단계부터 다시 실행
```

### RTSP 연결 실패 시

```bash
# GStreamer 사용
gst-launch-1.0 rtspsrc location="rtsp://..." ! decodebin ! autovideosink

# ffmpeg 사용
ffmpeg -i "rtsp://..." -vframes 1 test.jpg
```
