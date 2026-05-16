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
       └─ I/Q 원시값 → 진폭(sqrtf(I²+Q²)) 변환 (최대 64개)
            └─ FreeRTOS Queue
                 └─ HTTP POST → FastAPI /csi/raw  (바이너리 280바이트)
                       └─ Redis csi_log_stream
```

### FastAPI 전송 포맷

엔드포인트: `POST /csi/raw`  
Content-Type: `application/octet-stream`  
크기: **280바이트 고정** (little-endian 바이너리)

```
struct BinaryPacket {
    char     header[4];      // "CSI!"
    char     node_id[8];     // null-padded
    uint32_t detected_at;    // millis() 타임스탬프
    uint32_t seq_num;        // 단조 증가 카운터
    int32_t  rssi;
    float    csi_data[64];   // 진폭값 정확히 64개
};
// static_assert(sizeof(BinaryPacket) == 280)
```

Python 파싱 포맷 문자열: `"<4s8sIIi64f"`

### Redis csi_log_stream 스키마

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| node_id | String | String | NOTNULL | 기기 식별자 |
| seq_num | Integer | Int | NOTNULL | 패킷 순서 번호 |
| csi_matrix | JSON String | list[float] | NOTNULL | 64개 진폭값 |
| rssi | Integer | Int | NOTNULL | 신호 세기 |
| detected_at | Integer | Int | NOTNULL | 신호 발생 시각 (millis) |

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
| `FASTAPI_URL` | FastAPI 서버 주소 (예: `http://192.168.1.3:8000/csi/raw`) |

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

**13:00** — 빌드 테스트 (Step 4 완료)
- `pio run` 컴파일 성공, 에러 없음
- RAM 13.9% / Flash 27.7% 사용

---

**13:10** — 플래싱 및 Serial 모니터 동작 확인 (Step 5, 6 완료)
- `pio run --target upload` 플래싱 성공 (COM9, MAC: 1c:db:d4:47:12:d0)
- USB CDC 활성화 (`-DARDUINO_USB_CDC_ON_BOOT=1`) 추가로 Serial 출력 정상화
- WiFi 연결 확인, CSI 수집 및 HTTP POST 전송 동작 확인
- `POST 404` — FastAPI `/csi/log` 엔드포인트 미구현 상태, 펌웨어 자체는 정상

**13:15** — 전송 상태 LED 추가
- GPIO 48 온보드 LED, POST 전송 시 점등
- 50ms 간격으로 깜빡이며 송신 상태 시각화

**13:20** — WiFi 채널 13번 고정
- `esp_wifi_set_channel(13, WIFI_SECOND_CHAN_NONE)` 명시적 설정
- Station 모드 + 20MHz(HT20) 유지
- `#define CSI_WIFI_CHANNEL 13` 상수로 관리

### 2026-05-16 (오후)

**15:30** — 백엔드 바이너리 포맷에 맞게 전송 방식 전면 교체

**문제**: 펌웨어가 JSON을 전송하고 있었으나 백엔드(`csi_service.py`)는 280바이트 고정 바이너리 패킷만 수신 가능

변경 내용:
- `config.h` — URL `/csi/log` → `/csi/raw`, 서버 IP `192.168.1.2` → `192.168.1.3`
- `csi_collector.h` — `CSI_MAX_LEN` 128 → 64 (백엔드 포맷과 일치)
- `main.cpp` — JSON 직렬화 제거, `BinaryPacket` 구조체 정의 및 `http.POST(uint8_t*, size)` 바이너리 전송으로 교체
  - `static_assert(sizeof(BinaryPacket) == 280)` 컴파일 타임 크기 검증 추가
  - Content-Type `application/octet-stream`으로 변경
  - ArduinoJson 의존성 제거

---

## WiFi 설정

| 항목 | 값 |
|------|-----|
| 동작 모드 | Station (AP 연결) |
| 채널 | 13번 고정 |
| 대역폭 | 20MHz (WIFI_SECOND_CHAN_NONE) |
| FastAPI 서버 | 192.168.1.3:8000 |

---

## 다음 작업

- [x] Step 7: FastAPI `/csi/raw` 엔드포인트 연동 (바이너리 포맷으로 펌웨어 수정 완료)
- [ ] 플래싱 후 시리얼 모니터에서 `[OK] seq=X rssi=-XX csi_len=64` 확인
- [ ] Redis `csi_log_stream` 수신 확인 (`docker exec csi-redis-server redis-cli XLEN csi_log_stream`)
