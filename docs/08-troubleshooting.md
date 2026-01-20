# 08. 문제 해결 가이드

이 문서에서는 PPE 인식 시스템 구축 과정에서 발생할 수 있는 일반적인 문제와 해결 방법을 안내합니다.

## 목차
1. [Greengrass 설치 문제](#1-greengrass-설치-문제)
2. [컴포넌트 배포 문제](#2-컴포넌트-배포-문제)
3. [RTSP 스트림 문제](#3-rtsp-스트림-문제)
4. [PPE 모델 문제](#4-ppe-모델-문제)
5. [MQTT 통신 문제](#5-mqtt-통신-문제)
6. [성능 최적화](#6-성능-최적화)
7. [로그 분석](#7-로그-분석)

---

## 1. Greengrass 설치 문제

### 1.1 Java 관련 오류

**증상:**
```
Error: JAVA_HOME is not set or could not find java executable
```

**해결:**
```bash
# Java 설치 확인
java -version

# Java 미설치 시
sudo apt update
sudo apt install default-jdk -y

# JAVA_HOME 설정
echo 'export JAVA_HOME=/usr/lib/jvm/default-java' >> ~/.bashrc
source ~/.bashrc
```

### 1.2 권한 오류

**증상:**
```
Permission denied when creating /greengrass/v2
```

**해결:**
```bash
# sudo로 실행
sudo -E java -Droot="/greengrass/v2" ...

# 또는 디렉토리 생성 후 권한 부여
sudo mkdir -p /greengrass/v2
sudo chown -R $USER:$USER /greengrass/v2
```

### 1.3 AWS 자격 증명 오류

**증상:**
```
Unable to load AWS credentials from any provider
```

**해결:**
```bash
# AWS 자격 증명 확인
aws sts get-caller-identity

# 자격 증명 재설정
aws configure

# 환경 변수로 전달 (임시)
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=ap-northeast-2

# sudo에 환경 변수 전달
sudo -E java ...
```

### 1.4 네트워크 연결 오류

**증상:**
```
Unable to connect to AWS IoT data endpoint
```

**해결:**
```bash
# DNS 확인
nslookup iot.ap-northeast-2.amazonaws.com

# 포트 연결 테스트
nc -zv xxxxxx-ats.iot.ap-northeast-2.amazonaws.com 8883

# 방화벽 확인
sudo iptables -L

# 프록시 설정 (필요시)
export HTTPS_PROXY=http://proxy:port
```

### 1.5 Greengrass 서비스 시작 실패

**증상:**
```bash
sudo systemctl status greengrass
# Active: failed
```

**해결:**
```bash
# 로그 확인
sudo journalctl -u greengrass -n 100

# Greengrass 로그 확인
sudo cat /greengrass/v2/logs/greengrass.log

# 서비스 재시작
sudo systemctl restart greengrass

# 수동 실행 (디버그)
sudo /greengrass/v2/alts/current/distro/bin/loader
```

---

## 2. 컴포넌트 배포 문제

### 2.1 배포 상태 "FAILED"

**증상:**
AWS 콘솔에서 배포 상태가 FAILED

**진단:**
```bash
# 배포 상태 상세 확인
aws greengrassv2 get-deployment --deployment-id YOUR_DEPLOYMENT_ID

# 디바이스별 상태 확인
aws greengrassv2 list-effective-deployments \
  --core-device-thing-name RaspberryPi5-PPE
```

**일반적인 원인과 해결:**

| 원인 | 해결 |
|------|------|
| S3 접근 권한 부족 | S3 버킷 정책에 Greengrass 접근 허용 |
| 아티팩트 URI 오류 | recipe.yaml의 S3 URI 경로 확인 |
| 의존성 설치 실패 | requirements.txt 확인, 네트워크 확인 |
| 스크립트 오류 | Lifecycle 스크립트 문법 확인 |

### 2.2 컴포넌트 상태 "BROKEN"

**증상:**
```bash
sudo /greengrass/v2/bin/greengrass-cli component list
# State: BROKEN
```

**해결:**
```bash
# 컴포넌트 로그 확인
sudo cat /greengrass/v2/logs/com.example.PPEDetector.log

# 컴포넌트 재시작
sudo /greengrass/v2/bin/greengrass-cli component restart \
  --names com.example.PPEDetector

# 완전 재배포
sudo /greengrass/v2/bin/greengrass-cli deployment create \
  --remove com.example.PPEDetector
# 이후 다시 배포
```

### 2.3 Install 스크립트 실패

**증상:**
```
Installation script exited with code 1
```

**해결:**
```bash
# 수동으로 설치 스크립트 테스트
cd /greengrass/v2/packages/artifacts/com.example.PPEDetector/1.0.0/

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치 (에러 확인)
pip install -r requirements.txt
```

### 2.4 Run 스크립트 즉시 종료

**증상:**
컴포넌트가 시작 후 바로 종료됨

**해결:**
```bash
# 로그에서 에러 확인
sudo tail -100 /greengrass/v2/logs/com.example.PPEDetector.log

# 수동 실행 테스트
cd /greengrass/v2/packages/artifacts/com.example.PPEDetector/1.0.0/
source venv/bin/activate
python3 main.py
```

---

## 3. RTSP 스트림 문제

### 3.1 RTSP 연결 실패

**증상:**
```
Failed to connect to RTSP stream
OpenCV: FFMPEG: Connection refused
```

**진단:**
```bash
# 카메라 IP 연결 확인
ping 192.168.1.100

# RTSP 포트 확인
nc -zv 192.168.1.100 554

# ffmpeg로 스트림 테스트
ffmpeg -i "rtsp://admin:password@192.168.1.100:554/stream" -vframes 1 test.jpg

# GStreamer로 테스트
gst-launch-1.0 rtspsrc location="rtsp://..." ! decodebin ! fakesink
```

**해결:**

| 원인 | 해결 |
|------|------|
| 잘못된 URL | 카메라 제조사 문서에서 올바른 RTSP 경로 확인 |
| 인증 실패 | 사용자명/비밀번호 확인 |
| 방화벽 | 554, 8554 포트 허용 |
| 네트워크 분리 | 카메라와 같은 네트워크에 있는지 확인 |

### 3.2 프레임 읽기 지연/버퍼링

**증상:**
영상이 몇 초 지연되어 표시됨

**해결:**
```python
# OpenCV 버퍼 크기 최소화
cap = cv2.VideoCapture(rtsp_url)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# TCP 프로토콜 사용 (UDP 대신)
# URL에 추가: ?tcp 또는 환경변수
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
```

### 3.3 스트림 끊김

**증상:**
일정 시간 후 스트림이 끊어짐

**해결:**
```python
# 자동 재연결 로직 사용
class RTSPStreamReader:
    def read_frame(self):
        frame = self.cap.read()
        if frame is None:
            self.reconnect()  # 재연결 시도
```

```bash
# 네트워크 안정성 확인
ping -c 100 192.168.1.100 | grep -E "packet loss"
```

---

## 4. PPE 모델 문제

### 4.1 모델 로드 실패

**증상:**
```
Error loading model: No such file or directory
```

**해결:**
```bash
# 모델 파일 존재 확인
ls -la /opt/ppe-detector/models/

# 모델 경로가 올바른지 확인
echo $MODEL_PATH

# 모델 다운로드
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 4.2 추론 속도 느림

**증상:**
프레임당 처리 시간이 1초 이상

**해결:**
```python
# 더 작은 모델 사용
model = YOLO('yolov8n.pt')  # nano 버전

# 입력 이미지 크기 줄이기
results = model.predict(frame, imgsz=320)  # 기본 640 → 320

# 프레임 건너뛰기
if frame_count % 5 != 0:  # 5프레임마다 1번만 처리
    continue
```

### 4.3 감지 정확도 낮음

**증상:**
PPE를 제대로 감지하지 못함

**해결:**
```python
# 신뢰도 임계값 조정
results = model.predict(frame, conf=0.3)  # 0.5 → 0.3 (더 민감)

# PPE 전용 모델 사용
# Roboflow, Kaggle에서 PPE 데이터셋으로 훈련된 모델 찾기
```

### 4.4 메모리 부족

**증상:**
```
RuntimeError: CUDA out of memory
MemoryError: Unable to allocate array
```

**해결:**
```bash
# GPU 메모리 확인 (CUDA 사용 시)
nvidia-smi

# 시스템 메모리 확인
free -h

# swap 메모리 추가
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

```python
# CPU 사용 강제
results = model.predict(frame, device='cpu')

# 배치 크기 줄이기
results = model.predict(frames, batch=1)
```

---

## 5. MQTT 통신 문제

### 5.1 메시지 발행 실패

**증상:**
```
Failed to publish message to IoT Core
```

**진단:**
```bash
# IoT 정책 확인
aws iot get-policy --policy-name PPEDetectorPolicy

# 인증서 연결 확인
aws iot list-thing-principals --thing-name RaspberryPi5-PPE
```

**해결:**

IoT 정책에 필요한 권한 추가:
```json
{
  "Effect": "Allow",
  "Action": ["iot:Publish"],
  "Resource": ["arn:aws:iot:ap-northeast-2:*:topic/ppe/*"]
}
```

### 5.2 Greengrass IPC 오류

**증상:**
```
awsiot.greengrasscoreipc: Connection refused
```

**해결:**
```bash
# Greengrass 서비스 실행 확인
sudo systemctl status greengrass

# IPC 소켓 확인
ls -la /greengrass/v2/ipc.socket

# 컴포넌트 권한 확인 (recipe.yaml)
# accessControl 섹션이 올바른지 확인
```

### 5.3 메시지 미수신 (AWS 콘솔)

**증상:**
MQTT 테스트 클라이언트에서 메시지가 안 보임

**해결:**
```
1. 토픽 구독 확인: ppe/# (와일드카드)
2. 리전 확인: 올바른 리전(ap-northeast-2) 선택
3. MQTT 브릿지 컴포넌트 확인:
   - aws.greengrass.clientdevices.mqtt.Bridge 배포 필요
```

---

## 6. 성능 최적화

### 6.1 라즈베리파이5 최적화

```bash
# GPU 메모리 할당 증가
sudo raspi-config
# Advanced Options → Memory Split → 256

# CPU 거버너 performance 모드
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 불필요한 서비스 중지
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

### 6.2 Python 최적화

```python
# OpenCV 최적화 빌드 확인
print(cv2.getBuildInformation())

# NumPy 멀티스레딩
import os
os.environ['OMP_NUM_THREADS'] = '4'

# 프로파일링
import cProfile
cProfile.run('detect(frame)')
```

### 6.3 처리 파이프라인 최적화

```python
# 비동기 처리
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    # 프레임 읽기와 처리를 병렬로
    future = executor.submit(detector.detect, frame)
    next_frame = stream.read_frame()
    detections = future.result()
```

---

## 7. 로그 분석

### 7.1 로그 위치

| 로그 | 경로 |
|------|------|
| Greengrass 코어 | `/greengrass/v2/logs/greengrass.log` |
| 컴포넌트 | `/greengrass/v2/logs/<ComponentName>.log` |
| 시스템 | `/var/log/syslog` |

### 7.2 로그 레벨 변경

```bash
# Greengrass 로그 레벨 변경
sudo nano /greengrass/v2/config/effectiveConfig.yaml
```

```yaml
services:
  aws.greengrass.Nucleus:
    configuration:
      logging:
        level: DEBUG  # ERROR, WARN, INFO, DEBUG, TRACE
```

### 7.3 유용한 로그 분석 명령

```bash
# 에러만 필터링
sudo grep -i error /greengrass/v2/logs/*.log

# 최근 에러 시간순
sudo grep -i error /greengrass/v2/logs/*.log | tail -50

# 실시간 에러 모니터링
sudo tail -f /greengrass/v2/logs/*.log | grep -i --line-buffered error

# 특정 시간대 로그
sudo awk '/2024-01-15 10:3/' /greengrass/v2/logs/greengrass.log
```

### 7.4 CloudWatch 로그 쿼리

CloudWatch Logs Insights에서:
```
fields @timestamp, @message
| filter @logStream like /com.example.PPEDetector/
| filter @message like /error/i
| sort @timestamp desc
| limit 100
```

---

## 빠른 진단 체크리스트

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        문제 진단 체크리스트                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Greengrass 상태 확인                                                │
│     □ sudo systemctl status greengrass                                 │
│     □ sudo /greengrass/v2/bin/greengrass-cli component list            │
│                                                                         │
│  2. 로그 확인                                                           │
│     □ sudo tail -100 /greengrass/v2/logs/greengrass.log               │
│     □ sudo tail -100 /greengrass/v2/logs/com.example.PPEDetector.log  │
│                                                                         │
│  3. 네트워크 확인                                                       │
│     □ ping 8.8.8.8 (인터넷)                                            │
│     □ ping 192.168.1.100 (카메라)                                      │
│     □ nc -zv xxx.iot.ap-northeast-2.amazonaws.com 8883                │
│                                                                         │
│  4. AWS 연결 확인                                                       │
│     □ aws sts get-caller-identity                                      │
│     □ aws iot describe-thing --thing-name RaspberryPi5-PPE            │
│                                                                         │
│  5. 리소스 확인                                                         │
│     □ free -h (메모리)                                                 │
│     □ df -h (디스크)                                                   │
│     □ top (CPU)                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 도움 요청

문제가 해결되지 않으면:

1. **AWS 문서**: https://docs.aws.amazon.com/greengrass/
2. **AWS 포럼**: https://repost.aws/
3. **GitHub Issues**: 이 저장소의 Issues 탭
4. **AWS Support**: 유료 지원 플랜 사용 시

---

## 체크리스트

- [ ] 일반적인 오류 유형 이해
- [ ] 로그 확인 방법 숙지
- [ ] 진단 명령어 숙지
- [ ] 성능 최적화 기법 이해
