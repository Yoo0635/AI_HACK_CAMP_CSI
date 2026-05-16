# CSI AI — Raspberry Pi ARM64

## 개요

ESP32-S3로부터 수집된 WiFi CSI 데이터를 분석해 활동을 분류하고 위험도와 자연어 요약을 생성하는 추론 서버.

- 타겟: Raspberry Pi (ARM64)
- 런타임: TFLite INT8 (CNN+LSTM) + llama.cpp (sLLM)
- 인터페이스: Redis 스트림 (입력/출력)

---

## 설명

### 처리 흐름

```
Redis CsiLogStream  (stream당 200개 / 초당 20개)
  └─ worker.py (데몬)
       └─ orchestrator.py
            ├─ preprocessing.py     # 20샘플 슬라이딩 윈도우
            └─ model_engine.py      # TFLite CNN+LSTM 추론
                 └─ Redis CsiAnalysisStream  (stream당 600개 / 초당 1개)
                      └─ is_anomaly = true 일 때만
                           └─ llama_cpp_wrapper.py  # sLLM 자연어 요약
                                └─ Redis CsiAlertStream  (WebSocket 전달)
```

### Redis 입력 스키마 (CsiLogStream)

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| node_id | String | String | NOTNULL | 기기 식별자 |
| seq_num | Integer | Int | NOTNULL | 패킷 순서 번호 |
| csi_matrix | JSON String | list[float] | NOTNULL | 전처리 CSI 데이터 |
| rssi | Integer | Int | NOTNULL | 신호 세기 |
| detected_at | Integer | Int | NOTNULL | 신호 발생 시각 |

> stream 당 200개 보관 / 초당 20개 수신

### CNN 입출력

| 구분 | 필드 | 타입 |
|------|------|------|
| INPUT | csi_matrix | list[float] |
| INPUT | detected_at | Int |
| INPUT | node_id | String |
| OUTPUT | label | String |
| OUTPUT | score | Float |
| OUTPUT | energy | Float |
| OUTPUT | is_anomaly | Bool |
| OUTPUT | cnn_timestamp | Integer |
| OUTPUT | risk_score | Float |

### Redis 분석 결과 스키마 (CsiAnalysisStream)

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| node_id | String | String | NOTNULL | 기기 식별자 |
| seq_num | Integer | Int | NOTNULL | 패킷 순서 번호 |
| label | String | String | NOTNULL | 현재 상태 판정 |
| cnn_score | Float | Float | NOTNULL | CNN 판단 확신도 |
| energy | Float | Float | NOTNULL | 활동량 수치 (신호 흔들림 강도) |
| is_anomaly | Boolean | Bool | NOTNULL | 문제 발생 유무 |
| cnn_timestamp | Integer | Int | NOTNULL | CNN 분석 완료 시각 |
| risk_score | Float | Float | NOTNULL | 실제 위험 지수 |

> stream 당 600개 보관 / 초당 1개 출력

### sLLM 입출력

| 구분 | 필드 | 타입 |
|------|------|------|
| INPUT | label | String |
| INPUT | score | Float |
| INPUT | energy | Float |
| INPUT | is_anomaly | Bool |
| INPUT | timestamp | Integer |
| OUTPUT | llm_summary | String (Text) |
| OUTPUT | risk_advice | String (Text) |
| OUTPUT | sllm_timestamp | Integer |

### Redis 알림 스키마 (CsiAlertStream)

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| bed_id | String | String | NOTNULL | 침대 식별자 |
| nickname | String | String | NOTNULL | 병상 환자 이름 |
| label | String | String | NOTNULL | 현재 상태 |
| cnn_timestamp | Integer | Int | NOTNULL | 신호 발생 시각 |
| sllm_summary | Text | String | NOTNULL | AI 응답 |
| risk_score | Float | Float | NOTNULL | 실제 위험 지수 |

> is_anomaly = true 일 때만 발행 / WebSocket으로 프론트엔드 전달

알림 메시지 포맷:
```
${bed_id}침대 ${nickname}환자의 위험합니다
현재 상태: ${label}, 신호 발생 시각: ${cnn_timestamp}
AI 응답: ${sllm_summary}
위험 지수: ${risk_score}
```

### 파일 구조

```
ai/
├── Dockerfile                       # 라즈베리파이 ARM64 배포용
├── requirements.txt
├── .env.example
├── models/
│   ├── activity_cnn_int8.tflite     # 활동 분류 CNN+LSTM (저장소 포함)
│   ├── sllm_model.gguf              # sLLM 모델 ← 별도 다운로드 필요
│   └── download_models.sh           # gguf 다운로드 스크립트
├── src/
│   ├── worker.py                    # 메인 실행 파일 (Redis 데몬)
│   ├── config.py                    # .env 로드 및 전역 설정
│   ├── core/
│   │   ├── orchestrator.py          # 전체 파이프라인 조율
│   │   └── risk_scoring.py          # 위험도 산출 로직
│   ├── activity_engine/
│   │   ├── model_engine.py          # TFLite 추론
│   │   └── preprocessing.py         # 20샘플 슬라이딩 윈도우 전처리
│   └── summary_engine/
│       └── llama_cpp_wrapper.py     # sLLM 호출 래퍼
└── tools/
    ├── test_local.py                # 로컬 추론 테스트
    ├── data_collector.py            # 현장 학습 데이터 수집기
    ├── train.py                     # CNN+LSTM 학습 및 TFLite 변환
    └── eval_model.py                # 클래스별 정확도 평가
```

### 초기 설정 방법

`.env.example`을 복사해 `.env`로 만든 후 값 입력:

| 항목 | 설명 |
|------|------|
| `REDIS_URL` | Redis 서버 주소 (예: `redis://192.168.1.2:6379`) |
| `CSI_STREAM` | 입력 스트림 키 (기본값: `CsiLogStream`) |
| `ANALYSIS_STREAM` | CNN 결과 스트림 키 (기본값: `CsiAnalysisStream`) |
| `ALERT_STREAM` | 알림 스트림 키 (기본값: `CsiAlertStream`) |
| `TFLITE_MODEL_PATH` | TFLite 모델 경로 (기본값: `models/activity_cnn_int8.tflite`) |
| `GGUF_MODEL_PATH` | sLLM 모델 경로 (기본값: `models/sllm_model.gguf`) |
| `RISK_THRESHOLD` | 위험도 알림 임계값 (0.0 ~ 1.0) |

sLLM 모델 다운로드:

```bash
bash models/download_models.sh
```

---

## 개발 로그

### 2026-05-16

**13:00** — 프로젝트 구조 설계 확정
- 디렉터리 구조 확정 (src/, tools/, models/ 분리)
- `.env.example`, `config.py`, `download_models.sh` 추가 결정

**13:30** — 스켈레톤 파일 생성 (Step 2 완료)
- 전체 디렉터리 구조 및 파일 스텁 생성
- 스트림 설계 확정: CsiLogStream → CsiAnalysisStream → CsiAlertStream
- CNN / sLLM 입출력 스키마 확정
- git init, `ai` 브랜치 생성 및 GitHub push

---

## 다음 작업

- [ ] `src/config.py` — .env 로드 및 전역 설정 구현
- [ ] `src/activity_engine/preprocessing.py` — 슬라이딩 윈도우 구현
- [ ] `src/activity_engine/model_engine.py` — TFLite 추론 구현
- [ ] `src/core/risk_scoring.py` — 위험도 산출 로직 구현
- [ ] `src/summary_engine/llama_cpp_wrapper.py` — sLLM 래퍼 구현
- [ ] `src/core/orchestrator.py` — 파이프라인 조율 구현
- [ ] `src/worker.py` — Redis 데몬 구현
- [ ] `tools/test_local.py` — 로컬 추론 테스트
