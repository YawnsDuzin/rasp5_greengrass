# 07. 컴포넌트 배포 및 관리

이 문서에서는 개발한 PPE 인식 컴포넌트를 AWS 콘솔과 CLI를 통해 배포하고 관리합니다.

## 목차
1. [배포 전 준비](#1-배포-전-준비)
2. [AWS 콘솔에서 배포](#2-aws-콘솔에서-배포)
3. [AWS CLI로 배포](#3-aws-cli로-배포)
4. [배포 모니터링](#4-배포-모니터링)
5. [컴포넌트 업데이트](#5-컴포넌트-업데이트)
6. [롤백 및 삭제](#6-롤백-및-삭제)

---

## 1. 배포 전 준비

### 1.1 체크리스트

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        배포 전 체크리스트                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AWS 설정:                                                              │
│  ☐ IAM 역할/정책 생성 완료                                              │
│  ☐ IoT Core Thing 생성 완료                                            │
│  ☐ S3 버킷 생성 및 정책 설정 완료                                       │
│                                                                         │
│  라즈베리파이:                                                          │
│  ☐ Greengrass V2 설치 및 실행 중                                       │
│  ☐ AWS 콘솔에서 디바이스 상태 "정상" 확인                               │
│  ☐ Python, OpenCV, PyTorch 설치 완료                                   │
│                                                                         │
│  컴포넌트:                                                              │
│  ☐ 소스 코드 테스트 완료                                                │
│  ☐ 아티팩트 ZIP 생성 완료                                               │
│  ☐ S3에 아티팩트 업로드 완료                                            │
│  ☐ 레시피 파일 준비 완료                                                │
│                                                                         │
│  네트워크:                                                              │
│  ☐ IP 카메라 RTSP 스트림 접근 가능                                     │
│  ☐ 라즈베리파이 → AWS 인터넷 연결 확인                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 아티팩트 S3 업로드 확인

```bash
# S3 버킷 내용 확인
aws s3 ls s3://YOUR_BUCKET_NAME/components/com.example.PPEDetector/1.0.0/ --recursive

# 예상 출력:
# 2024-01-15 10:30:00    1234567 components/com.example.PPEDetector/1.0.0/ppe-detector.zip
```

### 1.3 Greengrass 디바이스 상태 확인

```bash
# 라즈베리파이에서 실행
sudo systemctl status greengrass

# Greengrass 로그 확인
sudo tail -f /greengrass/v2/logs/greengrass.log
```

---

## 2. AWS 콘솔에서 배포

### 2.1 컴포넌트 생성

1. AWS 콘솔에서 **IoT Greengrass** 서비스 접속
2. 좌측 메뉴 **"컴포넌트(Components)"** 클릭
3. **"컴포넌트 생성(Create component)"** 클릭

```
┌─────────────────────────────────────────────────────────────┐
│                      컴포넌트 생성                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  컴포넌트 소스:                                              │
│  (●) 레시피를 새 컴포넌트로 입력                             │
│  ( ) 기존 컴포넌트를 새 버전의 기반으로 사용                  │
│  ( ) S3에서 레시피 가져오기                                  │
│                                                             │
│  레시피 형식:                                                │
│  (●) YAML                                                   │
│  ( ) JSON                                                   │
│                                                             │
│  레시피:                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ RecipeFormatVersion: "2020-01-25"                   │   │
│  │ ComponentName: com.example.PPEDetector              │   │
│  │ ComponentVersion: "1.0.0"                           │   │
│  │ ...                                                 │   │
│  │                                                     │   │
│  │ (configs/recipe.yaml 내용 붙여넣기)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [컴포넌트 생성]                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 배포 생성

1. 좌측 메뉴 **"배포(Deployments)"** 클릭
2. **"배포 생성(Create deployment)"** 클릭

#### 2.2.1 대상 지정

```
┌─────────────────────────────────────────────────────────────┐
│                 1단계: 배포 대상 지정                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  배포 이름: [PPE-Detector-Deployment      ]                 │
│                                                             │
│  배포 대상:                                                  │
│  (●) 코어 디바이스                                          │
│  ( ) 사물 그룹                                              │
│                                                             │
│  대상 이름: [RaspberryPi5-PPE             ▼]                │
│                                                             │
│  [다음]                                                      │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.2 컴포넌트 선택

```
┌─────────────────────────────────────────────────────────────┐
│                 2단계: 컴포넌트 선택                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  내 컴포넌트:                                                │
│  ☑ com.example.PPEDetector (1.0.0)                         │
│                                                             │
│  공용 컴포넌트 (선택 추가):                                  │
│  ☑ aws.greengrass.Cli (2.12.x)                             │
│  ☑ aws.greengrass.LogManager (2.3.x)                       │
│  ☐ aws.greengrass.clientdevices.mqtt.Bridge                │
│                                                             │
│  [다음]                                                      │
└─────────────────────────────────────────────────────────────┘
```

**권장 추가 컴포넌트:**
- `aws.greengrass.Cli` - 로컬 CLI 사용
- `aws.greengrass.LogManager` - CloudWatch 로그 전송

#### 2.2.3 컴포넌트 구성

```
┌─────────────────────────────────────────────────────────────┐
│                 3단계: 컴포넌트 구성                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  com.example.PPEDetector 구성:                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ {                                                   │   │
│  │   "rtspUrl": "rtsp://admin:pass@192.168.1.100/s1", │   │
│  │   "confidenceThreshold": "0.5",                     │   │
│  │   "alertTopic": "ppe/alerts",                       │   │
│  │   "statusTopic": "ppe/status",                      │   │
│  │   "requiredPpe": "hardhat,safety_vest"             │   │
│  │ }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  aws.greengrass.LogManager 구성:                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ {                                                   │   │
│  │   "logsUploaderConfiguration": {                    │   │
│  │     "systemLogsConfiguration": {                    │   │
│  │       "uploadToCloudWatch": "true"                  │   │
│  │     },                                              │   │
│  │     "componentLogsConfiguration": [                 │   │
│  │       {                                             │   │
│  │         "componentName": "com.example.PPEDetector", │   │
│  │         "minimumLogLevel": "INFO"                   │   │
│  │       }                                             │   │
│  │     ]                                               │   │
│  │   }                                                 │   │
│  │ }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [다음]                                                      │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.4 고급 설정

```
┌─────────────────────────────────────────────────────────────┐
│                 4단계: 고급 설정                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  배포 정책:                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 컴포넌트 업데이트 정책:                              │   │
│  │ (●) 업데이트 시 컴포넌트 실행 중지 알림              │   │
│  │ ( ) 실행 중인 컴포넌트 건너뛰기                      │   │
│  │                                                     │   │
│  │ 타임아웃:                                           │   │
│  │ 구성 유효성 검사 타임아웃: [60   ] 초               │   │
│  │ 배포 타임아웃: [600  ] 초                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  실패 처리:                                                  │
│  (●) 아무 작업도 하지 않음                                  │
│  ( ) 롤백                                                   │
│                                                             │
│  [다음]                                                      │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.5 검토 및 배포

```
┌─────────────────────────────────────────────────────────────┐
│                 5단계: 검토                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  배포 정보:                                                  │
│  - 이름: PPE-Detector-Deployment                           │
│  - 대상: RaspberryPi5-PPE (코어 디바이스)                   │
│                                                             │
│  컴포넌트:                                                   │
│  - com.example.PPEDetector (1.0.0)                         │
│  - aws.greengrass.Cli (2.12.6)                             │
│  - aws.greengrass.LogManager (2.3.7)                       │
│                                                             │
│  [배포]                                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. AWS CLI로 배포

### 3.1 컴포넌트 등록

```bash
# 컴포넌트 생성 (레시피 파일 사용)
aws greengrassv2 create-component-version \
  --inline-recipe fileb://configs/recipe.yaml \
  --region ap-northeast-2

# 응답 예시:
# {
#     "arn": "arn:aws:greengrass:ap-northeast-2:123456789012:components:com.example.PPEDetector:versions:1.0.0",
#     "componentName": "com.example.PPEDetector",
#     "componentVersion": "1.0.0",
#     "status": {
#         "componentState": "DEPLOYABLE"
#     }
# }
```

### 3.2 배포 생성

```bash
# 배포 설정 JSON 파일 생성
cat > deployment.json << 'EOF'
{
    "targetArn": "arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE",
    "deploymentName": "PPE-Detector-Deployment",
    "components": {
        "com.example.PPEDetector": {
            "componentVersion": "1.0.0",
            "configurationUpdate": {
                "merge": "{\"rtspUrl\":\"rtsp://admin:password@192.168.1.100:554/stream\",\"confidenceThreshold\":\"0.5\"}"
            }
        },
        "aws.greengrass.Cli": {
            "componentVersion": "2.12.6"
        }
    },
    "deploymentPolicies": {
        "componentUpdatePolicy": {
            "timeoutInSeconds": 60,
            "action": "NOTIFY_COMPONENTS"
        },
        "configurationValidationPolicy": {
            "timeoutInSeconds": 60
        },
        "failureHandlingPolicy": "DO_NOTHING"
    }
}
EOF

# 배포 실행
aws greengrassv2 create-deployment \
  --cli-input-json file://deployment.json \
  --region ap-northeast-2
```

### 3.3 배포 상태 확인

```bash
# 배포 목록 조회
aws greengrassv2 list-deployments \
  --target-arn arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE \
  --region ap-northeast-2

# 특정 배포 상태 조회
aws greengrassv2 get-deployment \
  --deployment-id YOUR_DEPLOYMENT_ID \
  --region ap-northeast-2
```

---

## 4. 배포 모니터링

### 4.1 AWS 콘솔에서 모니터링

1. **IoT Greengrass** → **배포(Deployments)** → 배포 선택

```
┌─────────────────────────────────────────────────────────────┐
│              배포 상세: PPE-Detector-Deployment              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  배포 상태: ● 완료됨 (Completed)                            │
│                                                             │
│  대상 디바이스 상태:                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 디바이스              상태        마지막 업데이트   │   │
│  │ RaspberryPi5-PPE     ✓ 성공      2분 전           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  타임라인:                                                   │
│  10:30:00  배포 생성됨                                      │
│  10:30:05  디바이스에 전달됨                                 │
│  10:30:10  컴포넌트 다운로드 시작                            │
│  10:32:00  설치 완료                                        │
│  10:32:05  실행 시작                                        │
│  10:32:10  배포 완료                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 라즈베리파이에서 확인

```bash
# 컴포넌트 목록 확인
sudo /greengrass/v2/bin/greengrass-cli component list

# 예상 출력:
# Components currently running in Greengrass:
# Component Name: com.example.PPEDetector
#     Version: 1.0.0
#     State: RUNNING
#
# Component Name: aws.greengrass.Cli
#     Version: 2.12.6
#     State: RUNNING

# 컴포넌트 상세 정보
sudo /greengrass/v2/bin/greengrass-cli component details \
  --name com.example.PPEDetector
```

### 4.3 로그 확인

```bash
# Greengrass 코어 로그
sudo tail -f /greengrass/v2/logs/greengrass.log

# PPE Detector 컴포넌트 로그
sudo tail -f /greengrass/v2/logs/com.example.PPEDetector.log

# 실시간 로그 모니터링 (여러 파일)
sudo tail -f /greengrass/v2/logs/*.log
```

### 4.4 CloudWatch 로그 확인

LogManager 컴포넌트를 배포한 경우:

1. AWS 콘솔 → **CloudWatch** → **로그 그룹**
2. `/aws/greengrass/GreengrassSystemComponent/...` 확인
3. `/aws/greengrass/UserComponent/...` 에서 컴포넌트 로그 확인

### 4.5 MQTT 메시지 확인

AWS IoT Core 테스트 클라이언트에서:

```
┌─────────────────────────────────────────────────────────────┐
│                    MQTT 테스트 클라이언트                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  구독 토픽: ppe/#                                           │
│                                                             │
│  수신된 메시지:                                              │
│  ─────────────────────────────────────────────────────────  │
│  토픽: ppe/status                                           │
│  {                                                          │
│    "timestamp": "2024-01-15T10:35:00Z",                    │
│    "thing_name": "RaspberryPi5-PPE",                       │
│    "status": "RUNNING",                                    │
│    "stats": {                                              │
│      "frames_processed": 150,                              │
│      "detections": 45,                                     │
│      "alerts_sent": 3                                      │
│    }                                                       │
│  }                                                          │
│  ─────────────────────────────────────────────────────────  │
│  토픽: ppe/alerts                                           │
│  {                                                          │
│    "timestamp": "2024-01-15T10:36:00Z",                    │
│    "alert_type": "missing_ppe",                            │
│    "missing_ppe": "hardhat",                               │
│    "severity": "HIGH"                                      │
│  }                                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 컴포넌트 업데이트

### 5.1 버전 업데이트 절차

```
버전 업데이트 흐름:

  1. 코드 수정
     └─▶ 로컬 테스트
          └─▶ 새 버전으로 recipe.yaml 수정 (1.0.0 → 1.1.0)
               └─▶ 새 아티팩트 ZIP 생성
                    └─▶ S3 업로드 (새 버전 경로)
                         └─▶ 컴포넌트 등록
                              └─▶ 배포 업데이트
```

### 5.2 새 버전 배포

```bash
# 1. 레시피 버전 수정
# configs/recipe.yaml에서:
# ComponentVersion: "1.0.0" → "1.1.0"

# 2. 새 아티팩트 업로드
aws s3 cp ppe-detector.zip \
  s3://YOUR_BUCKET_NAME/components/com.example.PPEDetector/1.1.0/ppe-detector.zip

# 3. 새 컴포넌트 버전 등록
aws greengrassv2 create-component-version \
  --inline-recipe fileb://configs/recipe.yaml \
  --region ap-northeast-2

# 4. 배포 업데이트
aws greengrassv2 create-deployment \
  --target-arn arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE \
  --deployment-name "PPE-Detector-v1.1.0" \
  --components '{"com.example.PPEDetector":{"componentVersion":"1.1.0"}}' \
  --region ap-northeast-2
```

### 5.3 설정만 변경

컴포넌트 버전은 그대로 유지하면서 설정만 변경:

```bash
aws greengrassv2 create-deployment \
  --target-arn arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE \
  --deployment-name "PPE-Detector-ConfigUpdate" \
  --components '{
    "com.example.PPEDetector": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "merge": "{\"confidenceThreshold\":\"0.6\",\"requiredPpe\":\"hardhat,safety_vest,safety_glasses\"}"
      }
    }
  }' \
  --region ap-northeast-2
```

---

## 6. 롤백 및 삭제

### 6.1 이전 버전으로 롤백

```bash
# 이전 배포 확인
aws greengrassv2 list-deployments \
  --target-arn arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE \
  --region ap-northeast-2

# 이전 버전으로 새 배포 생성
aws greengrassv2 create-deployment \
  --target-arn arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE \
  --deployment-name "PPE-Detector-Rollback" \
  --components '{"com.example.PPEDetector":{"componentVersion":"1.0.0"}}' \
  --region ap-northeast-2
```

### 6.2 컴포넌트 제거

```bash
# 빈 배포로 컴포넌트 제거
aws greengrassv2 create-deployment \
  --target-arn arn:aws:iot:ap-northeast-2:123456789012:thing/RaspberryPi5-PPE \
  --deployment-name "Remove-PPE-Detector" \
  --components '{}' \
  --region ap-northeast-2
```

### 6.3 컴포넌트 버전 삭제

```bash
# 컴포넌트 버전 삭제 (배포되지 않은 버전만)
aws greengrassv2 delete-component \
  --arn arn:aws:greengrass:ap-northeast-2:123456789012:components:com.example.PPEDetector:versions:1.0.0 \
  --region ap-northeast-2
```

### 6.4 배포 취소

```bash
# 진행 중인 배포 취소
aws greengrassv2 cancel-deployment \
  --deployment-id YOUR_DEPLOYMENT_ID \
  --region ap-northeast-2
```

---

## 요약

| 작업 | AWS 콘솔 | AWS CLI |
|------|---------|---------|
| 컴포넌트 등록 | Components → Create | `create-component-version` |
| 배포 생성 | Deployments → Create | `create-deployment` |
| 상태 확인 | Deployments → 선택 | `get-deployment` |
| 업데이트 | 새 배포 생성 | `create-deployment` (새 버전) |
| 롤백 | 이전 버전 배포 | `create-deployment` (이전 버전) |
| 삭제 | 빈 배포 | `delete-component` |

---

## 다음 단계

컴포넌트 배포가 완료되었습니다!

문제가 발생한 경우 다음 문서를 참조하세요.

➡️ [08. 문제 해결 가이드](08-troubleshooting.md)

---

## 체크리스트

- [ ] 컴포넌트 등록 완료
- [ ] 배포 생성 완료
- [ ] 디바이스에서 컴포넌트 실행 확인
- [ ] 로그 모니터링 설정
- [ ] MQTT 메시지 수신 확인
- [ ] 업데이트/롤백 절차 이해
