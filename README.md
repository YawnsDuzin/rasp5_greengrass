# 라즈베리파이5 + AWS IoT Greengrass PPE 인식 시스템

## 프로젝트 개요

이 프로젝트는 **라즈베리파이5**에서 **AWS IoT Greengrass V2**를 사용하여 RTSP 카메라 스트림을 실시간으로 수신하고, **PPE(Personal Protective Equipment, 개인보호장비)** 착용 여부를 AI 모델로 인식하는 완전한 엣지 컴퓨팅 솔루션입니다.

### PPE(개인보호장비)란?
작업장에서 근로자의 안전을 위해 착용하는 보호 장비:
- 안전모 (Hard Hat)
- 안전 조끼 (Safety Vest)
- 보안경 (Safety Glasses)
- 안전화 (Safety Boots)
- 장갑 (Gloves)

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS 클라우드                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  IAM         │  │  IoT Core    │  │  S3          │  │  CloudWatch  │   │
│  │  (권한관리)   │  │  (디바이스   │  │  (모델저장)   │  │  (로그/모니터)│   │
│  │              │  │   관리)      │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│          │                │                 │                 │            │
│          └────────────────┼─────────────────┼─────────────────┘            │
│                           │                 │                              │
│                  ┌────────┴─────────────────┴────────┐                     │
│                  │      IoT Greengrass Service       │                     │
│                  │      (컴포넌트 배포/관리)          │                     │
│                  └───────────────┬───────────────────┘                     │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │ MQTT/HTTPS
                                   │ (인터넷)
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                         라즈베리파이5 (엣지 디바이스)                         │
│  ┌───────────────────────────────┴───────────────────────────────────────┐ │
│  │                    Greengrass Core Device                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │ │
│  │  │ RTSP Receiver   │  │ PPE Detector    │  │ Alert Publisher │       │ │
│  │  │ (스트림 수신)    │──│ (AI 인식)       │──│ (알림 발송)     │       │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                   │                                        │
└───────────────────────────────────┼────────────────────────────────────────┘
                                    │ RTSP
                              ┌─────┴─────┐
                              │ IP Camera │
                              │ (CCTV)    │
                              └───────────┘
```

## 주요 기능

1. **실시간 영상 처리**: RTSP 프로토콜로 IP 카메라 스트림 수신
2. **AI 기반 PPE 인식**: YOLOv8 모델을 사용한 보호장비 착용 감지
3. **엣지 컴퓨팅**: 클라우드 전송 없이 로컬에서 실시간 처리
4. **원격 배포**: AWS 콘솔에서 모델 업데이트 및 컴포넌트 배포
5. **알림 시스템**: PPE 미착용 감지 시 AWS IoT Core로 알림 전송

## 필요 장비 및 서비스

### 하드웨어
| 장비 | 사양 | 비고 |
|------|------|------|
| 라즈베리파이5 | 8GB RAM 권장 | 4GB도 가능 |
| microSD 카드 | 64GB 이상 | Class 10 권장 |
| 전원 어댑터 | 5V 5A USB-C | 공식 어댑터 권장 |
| IP 카메라 | RTSP 지원 | ONVIF 호환 권장 |
| 이더넷 케이블 | Cat5e 이상 | WiFi도 가능 |

### AWS 서비스
| 서비스 | 용도 | 예상 비용 |
|--------|------|----------|
| AWS IoT Core | 디바이스 연결 및 메시지 | $0.08/백만 메시지 |
| AWS IoT Greengrass | 엣지 런타임 | 무료 (디바이스당) |
| Amazon S3 | 모델 파일 저장 | $0.023/GB/월 |
| AWS IAM | 권한 관리 | 무료 |
| Amazon CloudWatch | 로깅/모니터링 | $0.50/GB |

> **예상 월 비용**: 테스트 용도로 약 $1~5 수준

## 문서 목차

### 1단계: AWS 기초 설정
- [01. AWS 계정 생성 및 초기 설정](docs/01-aws-account-setup.md)
- [02. IAM 사용자 및 권한 설정](docs/02-iam-setup.md)

### 2단계: AWS IoT 서비스 설정
- [03. AWS IoT Core 설정](docs/03-iot-core-setup.md)
- [04. AWS IoT Greengrass 설정](docs/04-greengrass-setup.md)

### 3단계: 라즈베리파이 설정
- [05. 라즈베리파이5 환경 설정](docs/05-raspberry-pi-setup.md)

### 4단계: 컴포넌트 개발 및 배포
- [06. PPE 인식 컴포넌트 개발](docs/06-component-development.md)
- [07. 컴포넌트 배포 및 관리](docs/07-deployment.md)

### 5단계: 운영 및 유지보수
- [08. 문제 해결 가이드](docs/08-troubleshooting.md)

## 빠른 시작

전체 과정을 순서대로 진행하세요:

```bash
# 1. 이 저장소 클론
git clone https://github.com/YawnsDuzin/rasp5_greengrass.git
cd rasp5_greengrass

# 2. AWS 계정 설정 (docs/01-aws-account-setup.md 참조)

# 3. 라즈베리파이 환경 설정
./scripts/setup_raspberry_pi.sh

# 4. Greengrass 설치 및 설정
./scripts/install_greengrass.sh

# 5. PPE 인식 컴포넌트 배포
./scripts/deploy_component.sh
```

## 프로젝트 구조

```
rasp5_greengrass/
├── README.md                          # 이 파일
├── docs/                              # 상세 문서
│   ├── 01-aws-account-setup.md       # AWS 계정 설정
│   ├── 02-iam-setup.md               # IAM 설정
│   ├── 03-iot-core-setup.md          # IoT Core 설정
│   ├── 04-greengrass-setup.md        # Greengrass 설정
│   ├── 05-raspberry-pi-setup.md      # 라즈베리파이 설정
│   ├── 06-component-development.md   # 컴포넌트 개발
│   ├── 07-deployment.md              # 배포 가이드
│   └── 08-troubleshooting.md         # 문제 해결
├── src/                               # 소스 코드
│   ├── components/                    # Greengrass 컴포넌트
│   │   └── ppe_detector/             # PPE 인식 컴포넌트
│   │       ├── main.py               # 메인 실행 파일
│   │       ├── rtsp_stream.py        # RTSP 스트림 처리
│   │       ├── ppe_model.py          # PPE 인식 모델
│   │       ├── mqtt_publisher.py     # MQTT 메시지 발행
│   │       └── requirements.txt      # Python 의존성
│   └── models/                        # ML 모델 관련
│       └── download_model.py         # 모델 다운로드 스크립트
├── configs/                           # 설정 파일
│   ├── config.yaml                   # 메인 설정
│   └── recipe.yaml                   # Greengrass 컴포넌트 레시피
├── scripts/                           # 유틸리티 스크립트
│   ├── setup_raspberry_pi.sh         # 라즈베리파이 초기 설정
│   ├── install_greengrass.sh         # Greengrass 설치
│   └── deploy_component.sh           # 컴포넌트 배포
└── assets/                            # 이미지 등 리소스
    └── architecture.png              # 아키텍처 다이어그램
```

## 용어 설명

AWS를 처음 사용하는 분들을 위한 핵심 용어 정리:

| 용어 | 설명 |
|------|------|
| **AWS IoT Core** | 수십억 개의 IoT 디바이스를 연결하고 관리하는 AWS 서비스 |
| **AWS IoT Greengrass** | 엣지 디바이스에서 로컬 컴퓨팅, 메시징, ML 추론을 실행하는 서비스 |
| **Greengrass Core Device** | Greengrass 소프트웨어가 설치된 디바이스 (여기서는 라즈베리파이) |
| **컴포넌트 (Component)** | Greengrass에서 실행되는 소프트웨어 모듈 (우리가 만들 PPE 인식 프로그램) |
| **레시피 (Recipe)** | 컴포넌트의 메타데이터와 구성 정보를 담은 YAML/JSON 파일 |
| **MQTT** | IoT 디바이스 간 경량 메시징 프로토콜 |
| **IAM** | Identity and Access Management, AWS 리소스 접근 권한 관리 |
| **Thing** | AWS IoT에 등록된 디바이스를 나타내는 논리적 표현 |
| **인증서** | 디바이스가 AWS에 안전하게 연결하기 위한 디지털 인증서 |
| **RTSP** | Real Time Streaming Protocol, IP 카메라 영상 전송 프로토콜 |
| **엣지 컴퓨팅** | 클라우드 대신 데이터 소스 가까이에서 처리하는 컴퓨팅 방식 |

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

문제 보고나 개선 제안은 GitHub Issues를 통해 해주세요.
