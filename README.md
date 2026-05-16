# CSI Firmware — ESP32-S3 N16R8

## Firmware 개요

ESP32-S3 N16R8 보드에서 WiFi CSI(Channel State Information) 데이터를 수집하여 FastAPI 서버로 전송하는 펌웨어.

- 보드: ESP32-S3 N16R8 (Flash 16MB, OPI PSRAM 8MB)
- 프레임워크: Arduino (ESP-IDF 기반)
- 전송 속도: 초당 20패킷 (50ms 간격)

---

## 설명

### 전송 흐름

```
ESP32-S3
  └─ WiFi CSI 콜백 (esp_wifi_set_csi_rx_cb)
       └─ I/Q 원시값 → 진폭(sqrtf(I²+Q²)) 변환
            └─ FreeRTOS Queue
                 └─ HTTP POST → FastAPI /csi/log
                       └─ Redis CsiLogStream
```

### FastAPI 전송 포맷

엔드포인트: `POST /csi/log`

```json
{
  "node_id":     "esp32s3-4712D0",
  "seq_num":     42,
  "csi_matrix":  [0.12, 0.34, 0.56, "..."],
  "rssi":        -65,
  "detected_at": 1747382400
}
```

### Redis CsiLogStream 스키마

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| node_id | String | String | NOTNULL | 기기 식별자 |
| seq_num | Integer | Int | NOTNULL | 패킷 순서 번호 |
| csi_matrix | JSON String | list[float] | NOTNULL | 전처리 CSI 데이터 |
| rssi | Integer | Int | NOTNULL | 신호 세기 |
| detected_at | Integer | Int | NOTNULL | 신호 발생 시각 |

> stream 당 200개 보관 / 초당 20개 전송

### 파일 구조

```
firmware/
├─ src/
│   ├─ main.cpp             # WiFi 연결, POST 전송 루프
│   └─ csi_collector.cpp    # ESP-IDF CSI 콜백, Queue 처리
├─ include/
│   ├─ config.h             # 실제 설정값 (gitignore — 커밋 안됨)
│   ├─ config.example.h     # 설정 템플릿 (복사 후 config.h로 사용)
│   └─ csi_collector.h      # CsiPacket 구조체 및 인터페이스
└─ platformio.ini           # 보드 및 빌드 설정
```

### 초기 설정 방법

`include/config.example.h`를 복사해 `include/config.h`로 만든 후 값 입력:

| 항목 | 설명 |
|------|------|
| `WIFI_SSID` | 공유기 SSID |
| `WIFI_PASSWORD` | 공유기 비밀번호 |
| `NODE_ID` | ESP32 식별자 (공유기 장치 목록에서 확인) |
| `FASTAPI_URL` | FastAPI 서버 주소 (예: `http://192.168.1.2:8000/csi/log`) |

---

## 개발 로그

### 2026-05-16

**11:40** — PlatformIO 설치 (CLI + VS Code 익스텐션)

**11:50** — PlatformIO 프로젝트 초기화
- 보드: `esp32-s3-devkitc-1` / 플랫폼: `espressif32` / 프레임워크: `arduino`

**12:00** — `platformio.ini` N16R8 설정 완료
- Flash 16MB, OPI PSRAM 8MB, `huge_app.csv` 파티션

**12:05** — 기본 스켈레톤 작성
- `src/main.cpp`, `include/config.h`, `include/csi_collector.h`

**12:09** — GitHub 연결 및 push (`firmware` 브랜치)

**12:30** — `src/csi_collector.cpp` 구현 (Step 1 완료)
- ESP-IDF CSI 콜백 등록 (`esp_wifi_set_csi_rx_cb`)
- I/Q 원시값 → 진폭 변환 (`sqrtf(I²+Q²)`)
- FreeRTOS Queue (크기 10) 로 메인 루프에 전달

**12:45** — `src/main.cpp` 완성 (Step 2 완료)
- WiFi 연결 및 자동 재연결 로직
- 50ms 간격 타이밍 제어 (초당 20패킷)
- CSI 패킷 → JSON 직렬화 → HTTP POST

**12:55** — `include/config.h` 설정 완료 (Step 3 완료)
- `config.h` gitignore 처리 (보안)
- `config.example.h` 템플릿 추가
- WIFI_SSID, WIFI_PASSWORD, NODE_ID, FASTAPI_URL 입력

---

## 다음 작업

- [ ] Step 4: 빌드 테스트 (`pio run`)
- [ ] Step 5: 플래싱 (`pio run --target upload`)
- [ ] Step 6: Serial 모니터 동작 확인 (`pio device monitor`)
- [ ] Step 7: FastAPI 연동 테스트
