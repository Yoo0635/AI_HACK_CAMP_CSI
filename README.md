# CSI Firmware — ESP32-S3 N16R8

WiFi CSI 데이터를 수집하여 FastAPI 서버로 전송하는 펌웨어.

---

## 개발 로그

### 2026-05-16

**11:40** — PlatformIO 설치 (CLI + VS Code 익스텐션)

**11:50** — PlatformIO 프로젝트 초기화
- 보드: `esp32-s3-devkitc-1`
- 플랫폼: `espressif32`
- 프레임워크: `arduino`

**12:00** — `platformio.ini` N16R8 설정 완료
- Flash: 16MB (`huge_app.csv` 파티션)
- PSRAM: 8MB OPI (`qio_opi`)
- 라이브러리: `ArduinoJson 7.x`

**12:05** — 기본 스켈레톤 작성
- `src/main.cpp` — WiFi 연결, CSI 패킷 POST 루프
- `include/config.h` — WiFi SSID/PW, NODE_ID, FastAPI URL
- `include/csi_collector.h` — CsiPacket 구조체 및 인터페이스 정의

**12:09** — GitHub 연결 및 push (`firmware` 브랜치)

---

## 전송 포맷

FastAPI 엔드포인트: `POST /csi/log`

```json
{
  "node_id":    "esp32s3-node-01",
  "seq_num":    42,
  "csi_matrix": [0.12, -0.34, 0.56, "..."],
  "rssi":       -65,
  "detected_at": 1747382400
}
```

- 전송 속도: 초당 20개 (50ms 간격)
- csi_matrix: I/Q 원시값 → 진폭(`sqrt(I²+Q²)`) 변환 후 전송

---

## 다음 작업

- [ ] `src/csi_collector.cpp` — ESP-IDF CSI 콜백 구현
- [ ] WiFi config 실제 값 입력
- [ ] FastAPI URL 실제 서버 주소로 교체
- [ ] 빌드 및 플래싱 테스트
