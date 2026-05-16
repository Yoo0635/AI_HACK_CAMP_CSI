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
  "node_id":     "esp32s3-node-01",
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
│   ├─ main.cpp            # WiFi 연결, POST 전송 루프
│   └─ csi_collector.cpp   # ESP-IDF CSI 콜백, Queue 처리
├─ include/
│   ├─ config.h            # WiFi / FastAPI URL 설정
│   └─ csi_collector.h     # CsiPacket 구조체 및 인터페이스
└─ platformio.ini          # 보드 및 빌드 설정
```

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

---

## 다음 작업

- [ ] Step 2: `main.cpp` 완성 — WiFi 연결 후 50ms POST 루프
- [ ] Step 3: `config.h` 실제 값 입력
- [ ] Step 4: 빌드 테스트 (`pio run`)
