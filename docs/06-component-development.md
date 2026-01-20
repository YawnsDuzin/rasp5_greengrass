# 06. PPE 인식 컴포넌트 개발

이 문서에서는 PPE(개인보호장비) 인식 Greengrass 컴포넌트를 개발합니다.

## 목차
1. [컴포넌트 구조 이해](#1-컴포넌트-구조-이해)
2. [소스 코드 설명](#2-소스-코드-설명)
3. [PPE 인식 모델](#3-ppe-인식-모델)
4. [레시피 작성](#4-레시피-작성)
5. [로컬 테스트](#5-로컬-테스트)
6. [컴포넌트 패키징](#6-컴포넌트-패키징)

---

## 1. 컴포넌트 구조 이해

### 1.1 프로젝트 구조

```
src/components/ppe_detector/
├── main.py              # 메인 실행 파일 (진입점)
├── rtsp_stream.py       # RTSP 스트림 처리 모듈
├── ppe_model.py         # PPE 인식 모델 모듈
├── mqtt_publisher.py    # MQTT 메시지 발행 모듈
├── requirements.txt     # Python 의존성
└── models/              # ML 모델 파일 (추후 추가)
    └── ppe_yolov8n.pt
```

### 1.2 컴포넌트 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PPE Detector Component                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                   │
│  │  main.py        │ ◀─── 메인 제어 로직                                │
│  │  (Controller)   │      · 설정 로드                                  │
│  │                 │      · 컴포넌트 초기화                             │
│  │                 │      · 메인 루프 실행                              │
│  └────────┬────────┘                                                   │
│           │                                                             │
│  ┌────────┴────────┬─────────────────┬─────────────────┐               │
│  │                 │                 │                 │               │
│  ▼                 ▼                 ▼                 ▼               │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────┐     │
│ │rtsp_stream  │ │ppe_model    │ │mqtt_        │ │ Configuration │     │
│ │.py          │ │.py          │ │publisher.py │ │ (YAML/ENV)    │     │
│ │             │ │             │ │             │ │               │     │
│ │RTSP 스트림  │ │YOLOv8 모델  │ │MQTT 발행    │ │환경 설정      │     │
│ │수신/디코딩  │ │PPE 감지     │ │IoT Core 연동│ │               │     │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └───────────────┘     │
│        │               │               │                              │
│        ▼               │               ▼                              │
│  ┌──────────┐          │         ┌──────────────┐                     │
│  │IP Camera │          │         │ AWS IoT Core │                     │
│  │(RTSP)    │          │         │ MQTT Broker  │                     │
│  └──────────┘          │         └──────────────┘                     │
│                        │                                              │
│                        ▼                                              │
│                  ┌──────────┐                                         │
│                  │ YOLOv8   │                                         │
│                  │ Model    │                                         │
│                  │ (.pt)    │                                         │
│                  └──────────┘                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 데이터 흐름

```
IP 카메라                  PPE Detector                    AWS Cloud
┌─────────┐              ┌─────────────────┐             ┌─────────────┐
│         │    RTSP      │                 │    MQTT     │             │
│ Camera  │─────────────▶│ 1. 프레임 수신  │             │ IoT Core    │
│         │   H.264      │ 2. PPE 감지     │ ─ ─ ─ ─ ─ ▶│ (Broker)    │
│         │              │ 3. 규정 체크    │   알림      │             │
└─────────┘              │ 4. 알림 발행    │             └─────────────┘
                         └─────────────────┘                    │
                                                                │
                         메시지 예시:                            ▼
                         ┌─────────────────────────────┐  ┌──────────┐
                         │ {                          │  │Dashboard │
                         │   "alert_type": "missing", │  │ / App    │
                         │   "missing_ppe": "hardhat",│  └──────────┘
                         │   "timestamp": "...",      │
                         │   "severity": "HIGH"       │
                         │ }                          │
                         └─────────────────────────────┘
```

---

## 2. 소스 코드 설명

### 2.1 main.py - 메인 컨트롤러

메인 파일의 핵심 구성:

```python
class PPEDetectorComponent:
    """PPE 인식 Greengrass 컴포넌트 메인 클래스"""

    def __init__(self):
        # 설정 로드
        self.config = self._load_config()
        # 셧다운 이벤트 (Ctrl+C, SIGTERM 처리)
        self.shutdown_event = Event()

    def _load_config(self) -> dict:
        """환경 변수에서 설정 로드"""
        config = {
            'rtsp_url': os.environ.get('RTSP_URL', 'rtsp://...'),
            'confidence_threshold': float(os.environ.get('CONFIDENCE_THRESHOLD', '0.5')),
            'alert_topic': os.environ.get('ALERT_TOPIC', 'ppe/alerts'),
            # ...
        }
        return config

    def run(self):
        """메인 실행 루프"""
        while not self.shutdown_event.is_set():
            # 1. 프레임 읽기
            frame = self.stream_reader.read_frame()

            # 2. PPE 감지
            detections = self.ppe_detector.detect(frame)

            # 3. 규정 준수 확인
            alerts = self._check_ppe_compliance(detections)

            # 4. 알림 발행
            if alerts:
                self._publish_alerts(alerts)
```

### 2.2 rtsp_stream.py - RTSP 스트림 리더

```python
class RTSPStreamReader:
    """RTSP 스트림 비동기 읽기"""

    def __init__(self, rtsp_url: str, ...):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.frame_queue = Queue(maxsize=2)  # 버퍼 최소화

    def connect(self) -> bool:
        """RTSP 스트림 연결"""
        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 지연 최소화
        return self.cap.isOpened()

    def read_frame(self) -> np.ndarray:
        """프레임 읽기 (비차단)"""
        return self.frame_queue.get(timeout=1.0)
```

#### RTSP URL 형식

```
일반적인 RTSP URL 형식:
rtsp://[username]:[password]@[ip_address]:[port]/[stream_path]

예시:
- Hikvision: rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
- Dahua: rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0
- Generic: rtsp://admin:password@192.168.1.100:554/stream1

포트 기본값: 554
```

### 2.3 ppe_model.py - PPE 인식 모델

```python
class PPEDetector:
    """YOLOv8 기반 PPE 인식기"""

    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """프레임에서 PPE 감지"""
        results = self.model.predict(
            frame,
            conf=self.confidence_threshold,
            device='cpu'  # 라즈베리파이는 CPU 사용
        )

        detections = []
        for result in results:
            for box in result.boxes:
                detections.append({
                    'class': self._get_class_name(box.cls),
                    'confidence': float(box.conf),
                    'bbox': box.xyxy.tolist()
                })

        return detections
```

#### 지원 클래스

| 클래스 ID | 이름 | 설명 |
|-----------|------|------|
| 0 | `person` | 사람 |
| 1 | `hardhat` | 안전모 착용 |
| 2 | `no_hardhat` | 안전모 미착용 |
| 3 | `safety_vest` | 안전 조끼 착용 |
| 4 | `no_safety_vest` | 안전 조끼 미착용 |
| 5 | `safety_glasses` | 보안경 |
| 6 | `gloves` | 장갑 |
| 7 | `mask` | 마스크 |

### 2.4 mqtt_publisher.py - MQTT 퍼블리셔

```python
class MQTTPublisher:
    """AWS IoT Core로 메시지 발행"""

    def __init__(self, thing_name: str, use_greengrass_ipc: bool = True):
        if use_greengrass_ipc:
            # Greengrass IPC 사용 (권장)
            import awsiot.greengrasscoreipc as ipc
            self.ipc_client = ipc.connect()
        else:
            # 직접 MQTT 연결
            self._init_direct_mqtt()

    def publish(self, topic: str, payload: dict) -> bool:
        """메시지 발행"""
        message_json = json.dumps(payload)

        request = PublishToIoTCoreRequest(
            topic_name=topic,
            qos=QOS.AT_LEAST_ONCE,
            payload=message_json.encode()
        )

        operation = self.ipc_client.new_publish_to_iot_core()
        operation.activate(request)
        return True
```

---

## 3. PPE 인식 모델

### 3.1 모델 선택

| 모델 | 크기 | 속도 (라즈베리파이5) | 정확도 |
|------|------|---------------------|--------|
| YOLOv8n | 6MB | ~200ms/프레임 | 중 |
| YOLOv8s | 22MB | ~400ms/프레임 | 중상 |
| YOLOv8m | 52MB | ~800ms/프레임 | 상 |

**권장**: YOLOv8n (속도와 정확도 균형)

### 3.2 사전 훈련 모델 사용

#### 옵션 A: 기본 COCO 모델 (테스트용)

```python
from ultralytics import YOLO

# 기본 YOLOv8n 로드 (person 클래스만 감지)
model = YOLO('yolov8n.pt')
```

#### 옵션 B: PPE 전용 모델 사용

Roboflow, Kaggle 등에서 PPE 데이터셋으로 훈련된 모델 사용:

```python
# 커스텀 PPE 모델 로드
model = YOLO('/path/to/ppe_yolov8n.pt')
```

### 3.3 커스텀 모델 훈련 (선택사항)

```python
from ultralytics import YOLO

# 사전 훈련 모델 로드
model = YOLO('yolov8n.pt')

# PPE 데이터셋으로 파인튜닝
results = model.train(
    data='ppe_dataset.yaml',  # 데이터셋 설정
    epochs=100,
    imgsz=640,
    batch=16,
    device='cpu'  # 또는 'cuda'
)

# 모델 저장
model.export(format='pt')
```

### 3.4 모델 다운로드 스크립트

```bash
# src/models/download_model.py 실행
cd /opt/ppe-detector
python3 src/models/download_model.py
```

---

## 4. 레시피 작성

### 4.1 레시피 구조

`configs/recipe.yaml`:

```yaml
RecipeFormatVersion: "2020-01-25"

ComponentName: com.example.PPEDetector
ComponentVersion: "1.0.0"
ComponentDescription: PPE Detection Component

# 의존성
ComponentDependencies:
  aws.greengrass.Nucleus:
    VersionRequirement: ">=2.9.0"
    DependencyType: HARD

# 플랫폼 설정
Manifests:
  - Platform:
      os: linux
      architecture: aarch64  # ARM64 (라즈베리파이5)

    Lifecycle:
      Install: |
        pip install -r {artifacts:decompressedPath}/requirements.txt

      Run: |
        python3 {artifacts:decompressedPath}/main.py

    Artifacts:
      - Uri: s3://your-bucket/components/ppe-detector.zip
        Unarchive: ZIP

# 설정
ComponentConfiguration:
  DefaultConfiguration:
    rtspUrl: "rtsp://192.168.1.100:554/stream"
    confidenceThreshold: "0.5"
    alertTopic: "ppe/alerts"
```

### 4.2 주요 레시피 요소

| 요소 | 설명 |
|------|------|
| **RecipeFormatVersion** | 레시피 형식 버전 (항상 "2020-01-25") |
| **ComponentName** | 컴포넌트 고유 식별자 (역도메인 형식 권장) |
| **ComponentVersion** | 시맨틱 버전 (x.y.z) |
| **ComponentDependencies** | 다른 컴포넌트에 대한 의존성 |
| **Manifests** | 플랫폼별 설치/실행 지침 |
| **Lifecycle** | Install, Run, Shutdown 스크립트 |
| **Artifacts** | 컴포넌트 파일 (S3 URI) |
| **ComponentConfiguration** | 기본 설정값 |

### 4.3 설정 변수 사용

레시피에서 설정값을 스크립트로 전달:

```yaml
Lifecycle:
  Run:
    Script: |
      export RTSP_URL="{configuration:/rtspUrl}"
      python3 main.py
```

Python에서 읽기:
```python
rtsp_url = os.environ.get('RTSP_URL')
```

---

## 5. 로컬 테스트

### 5.1 라즈베리파이에서 직접 테스트

```bash
# 프로젝트 디렉토리로 이동
cd /opt/ppe-detector

# 가상 환경 활성화
source venv/bin/activate

# 환경 변수 설정
export RTSP_URL="rtsp://admin:password@192.168.1.100:554/stream"
export CONFIDENCE_THRESHOLD="0.5"
export ALERT_TOPIC="ppe/alerts"
export MODEL_PATH="/opt/ppe-detector/models/ppe_yolov8n.pt"

# 테스트 실행
python3 src/components/ppe_detector/main.py
```

### 5.2 웹캠으로 테스트

```bash
# RTSP 대신 USB 웹캠 사용 (테스트용)
export RTSP_URL="0"  # 카메라 인덱스

python3 src/components/ppe_detector/main.py
```

### 5.3 개별 모듈 테스트

```bash
# RTSP 스트림 테스트
python3 src/components/ppe_detector/rtsp_stream.py --url "rtsp://..." --show

# PPE 모델 테스트
python3 src/components/ppe_detector/ppe_model.py --camera 0

# MQTT 퍼블리셔 테스트 (모의)
python3 src/components/ppe_detector/mqtt_publisher.py --mock --topic ppe/test
```

### 5.4 Greengrass CLI로 로컬 배포 테스트

```bash
# Greengrass CLI 사용
sudo /greengrass/v2/bin/greengrass-cli deployment create \
  --recipeDir /path/to/recipes \
  --artifactDir /path/to/artifacts \
  --merge "com.example.PPEDetector=1.0.0"

# 컴포넌트 상태 확인
sudo /greengrass/v2/bin/greengrass-cli component list

# 로그 확인
sudo tail -f /greengrass/v2/logs/com.example.PPEDetector.log
```

---

## 6. 컴포넌트 패키징

### 6.1 아티팩트 ZIP 생성

```bash
cd /home/user/rasp5_greengrass

# 패키징할 파일 준비
mkdir -p build/ppe-detector

# 소스 코드 복사
cp -r src/components/ppe_detector/* build/ppe-detector/

# 모델 파일 복사 (있으면)
cp models/ppe_yolov8n.pt build/ppe-detector/models/ 2>/dev/null || true

# ZIP 생성
cd build
zip -r ppe-detector.zip ppe-detector/

# 확인
unzip -l ppe-detector.zip
```

### 6.2 S3에 업로드

```bash
# AWS CLI 사용
aws s3 cp ppe-detector.zip \
  s3://YOUR_BUCKET_NAME/components/com.example.PPEDetector/1.0.0/ppe-detector.zip

# 업로드 확인
aws s3 ls s3://YOUR_BUCKET_NAME/components/com.example.PPEDetector/1.0.0/
```

### 6.3 레시피 URI 수정

`configs/recipe.yaml`의 Artifacts URI를 실제 S3 경로로 수정:

```yaml
Artifacts:
  - Uri: s3://YOUR_BUCKET_NAME/components/com.example.PPEDetector/1.0.0/ppe-detector.zip
```

### 6.4 컴포넌트 등록

AWS 콘솔 또는 CLI로 컴포넌트 등록:

```bash
# AWS CLI로 컴포넌트 생성
aws greengrassv2 create-component-version \
  --inline-recipe fileb://configs/recipe.yaml \
  --region ap-northeast-2
```

---

## 요약

이 문서에서 개발한 내용:

| 모듈 | 파일 | 기능 |
|------|------|------|
| 메인 컨트롤러 | `main.py` | 전체 흐름 제어, 설정 관리 |
| RTSP 리더 | `rtsp_stream.py` | 카메라 스트림 수신 |
| PPE 모델 | `ppe_model.py` | YOLOv8 기반 인식 |
| MQTT 퍼블리셔 | `mqtt_publisher.py` | AWS IoT Core 연동 |
| 레시피 | `recipe.yaml` | Greengrass 배포 설정 |

---

## 다음 단계

컴포넌트 개발이 완료되었습니다!

다음 문서에서는 **AWS 콘솔을 통해 컴포넌트를 배포**합니다.

➡️ [07. 컴포넌트 배포 및 관리](07-deployment.md)

---

## 체크리스트

- [ ] 소스 코드 구조 이해
- [ ] 각 모듈 기능 파악
- [ ] PPE 모델 준비 (기본 또는 커스텀)
- [ ] 레시피 파일 작성
- [ ] 로컬 테스트 완료
- [ ] 아티팩트 ZIP 생성
- [ ] S3 업로드 완료
