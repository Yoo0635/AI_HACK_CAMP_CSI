# CSI AI — Raspberry Pi ARM64

## 개요

ESP32 센서가 수집한 Wi-Fi CSI 신호를 분석해 침대 이탈·움직임·정상 수면을 분류하고, 이상 감지 시 sLLM이 자동으로 현황 요약을 생성하는 추론 서버.

- 타겟: Raspberry Pi (ARM64)
- 런타임: TFLite INT8 (CNN+LSTM) + llama.cpp (sLLM)
- 인터페이스: Redis 스트림 (입력/출력)

---

## 설명

### 처리 흐름

```
Redis csi_log_stream  (stream당 200개 / 초당 20개)
  └─ [CNN 루프 — 메인 스레드]
       ├─ preprocessing.py     # 20샘플 슬라이딩 윈도우 → (1, 20, 64, 2)
       ├─ model_engine.py      # TFLite CNN+LSTM 추론 → label, score, energy
       ├─ risk_scoring.py      # 위험도 산출 → risk_score, is_anomaly
       └─ csi_analysis_stream xadd

Redis csi_analysis_stream  (stream당 600개 / 초당 1개)
  └─ [LLM 스레드 — 데몬]
       └─ is_anomaly == "true" 일 때만
            └─ llama_cpp_wrapper.py  # EXAONE 추론 (10~30s)
                 └─ csi_analysis_stream xadd (sllm_summary 필드 추가)
```

> CNN 루프와 LLM 추론은 별도 스레드로 분리되어 CNN 실시간성을 보장

### Redis 입력 스키마 (csi_log_stream)

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| node_id | String | String | NOTNULL | ESP32 기기 ID |
| seq_num | Integer | Int | NOTNULL | 패킷 순서 번호 |
| csi_matrix | JSON String | list[float] | NOTNULL | 64개 진폭값 (0~150) |

> stream 당 200개 보관 / 초당 20개 수신

### CNN 입출력

| 구분 | 필드 | 타입 | 설명 |
|------|------|------|------|
| INPUT | node_id | String | 기기 식별자 |
| INPUT | csi_matrix | list[float] | 64개 진폭값 |
| OUTPUT | label | String | NORMAL / MOVE / FALL |
| OUTPUT | cnn_score | Float | CNN 신뢰도 (0~1) |
| OUTPUT | energy | Float | CSI 활동량 수치 |
| OUTPUT | is_anomaly | String | "true" / "false" |
| OUTPUT | cnn_timestamp | Integer | 분석 완료 시각 (Unix ms) |
| OUTPUT | risk_score | Float | 위험 지수 (0~100) |

### 분류 클래스 및 위험도 산출

| 클래스 | 설명 | 기본 점수 |
|--------|------|-----------|
| NORMAL | 침대에 누워 정지 | 20점 |
| MOVE | 침대 위 뒤척임·움직임 | 65점 |
| FALL | 침대 이탈 | 85점 |

```
risk_score = 기본점수 × CNN 신뢰도 + 에너지 보정 (최대 15점)
is_anomaly = "true"  if risk_score > 43
```

### Redis 분석 결과 스키마 (csi_analysis_stream)

| 필드 | DB 타입 | Python 타입 | 제약조건 | 설명 |
|------|---------|-------------|----------|------|
| node_id | String | String | NOTNULL | 기기 식별자 |
| seq_num | Integer | Int | NOTNULL | 패킷 순서 번호 |
| label | String | String | NOTNULL | 현재 상태 판정 |
| cnn_score | Float | Float | NOTNULL | CNN 판단 확신도 |
| energy | Float | Float | NOTNULL | 활동량 수치 |
| is_anomaly | String | String | NOTNULL | "true" / "false" |
| cnn_timestamp | Integer | Int | NOTNULL | CNN 분석 완료 시각 (Unix ms) |
| risk_score | Float | Float | NOTNULL | 위험 지수 (0~100) |
| sllm_summary | String | String | 조건부 | AI 요약 (is_anomaly="true" 시에만) |

> stream 당 600개 보관 / 초당 1개 출력

### sLLM 입출력

| 구분 | 필드 | 타입 |
|------|------|------|
| INPUT | label | String |
| INPUT | cnn_score | Float |
| INPUT | energy | Float |
| INPUT | is_anomaly | String |
| INPUT | cnn_timestamp | Integer |
| OUTPUT | sllm_summary | String |
| OUTPUT | sllm_timestamp | Integer |

### 모델 정보

#### 활동 분류 모델 — CNN+LSTM (TFLite INT8)

| 항목 | 내용 |
|------|------|
| 입력 shape | (1, 20, 64, 2) — 배치·프레임·서브캐리어·채널 |
| 채널 0 | amplitude: `clip(raw / 20.0, 0.0, 1.0)` |
| 채널 1 | Doppler: `clip(diff(raw, axis=time) / 5.0, -1.0, 1.0)` |
| 출력 | 3클래스 softmax (NORMAL / MOVE / FALL) |
| 파일 | `models/activity_cnn_int8.tflite` (~254 KB) |

#### 요약 생성 모델 — sLLM

| 항목 | 내용 |
|------|------|
| 모델 | EXAONE 3.5 2.4B Instruct |
| 제조사 | LG AI Research |
| 포맷 | GGUF Q4_K_M (4비트 양자화) |
| 파일 | `models/sllm_model.gguf` (~1.7 GB) |
| 선택 이유 | 한국어 특화, 라즈베리파이 ARM64 최적 추론 속도 |

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
│   ├── worker.py                    # 메인 실행 파일 (Redis 데몬, 2스레드)
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

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `REDIS_HOST` | `localhost` | Redis 서버 주소 |
| `REDIS_PORT` | `6379` | Redis 포트 |
| `CSI_STREAM_NAME` | `csi_log_stream` | 입력 스트림 키 |
| `CSI_RESULT_STREAM` | `csi_analysis_stream` | 출력 스트림 키 |
| `TFLITE_MODEL_PATH` | `models/activity_cnn_int8.tflite` | TFLite 모델 경로 |
| `GGUF_MODEL_PATH` | `models/sllm_model.gguf` | sLLM 모델 경로 |

sLLM 모델 다운로드:

```bash
pip install huggingface_hub
huggingface-cli download \
  bartowski/EXAONE-3.5-2.4B-Instruct-GGUF \
  EXAONE-3.5-2.4B-Instruct-Q4_K_M.gguf \
  --local-dir models/ \
  --local-dir-use-symlinks False

mv models/EXAONE-3.5-2.4B-Instruct-Q4_K_M.gguf models/sllm_model.gguf
```

---

## 개발 로그

### 2026-05-16

**13:00** — 프로젝트 구조 설계 확정
- 디렉터리 구조 확정 (src/, tools/, models/ 분리)
- `.env.example`, `config.py`, `download_models.sh` 추가 결정

**13:30** — 스켈레톤 파일 생성 완료
- 전체 디렉터리 구조 및 파일 스텁 생성
- git init, `ai` 브랜치 생성 및 GitHub push

**13:50** — `src/config.py` 구현 완료
- `.env` 로드 및 전역 설정 (REDIS_HOST, REDIS_PORT, 스트림 키, 모델 경로)

**14:10** — `src/activity_engine/preprocessing.py` 구현 완료
- `deque(maxlen=20)` 슬라이딩 윈도우 버퍼
- amplitude 채널: `clip(buf / 20.0, 0.0, 1.0)` → (20, 64)
- Doppler 채널: `clip(diff / 5.0, -1.0, 1.0)` + 첫 프레임 zero 패딩 → (20, 64)
- 모델 입력 shape: (1, 20, 64, 2)

**14:30** — `tools/data_collector.py` 구현 완료 (현장 도착)
- `--label NORMAL / MOVE / FALL` CLI 인자로 레이블 지정
- `--duration` 초 동안 `csi_log_stream` 구독 후 `.npy` 저장
- 파일명: `{LABEL}_{timestamp}_{n}samples.npy`
- 모델 입력 shape: (1, 20, 64, 2)

---

## 다음 작업

- [ ] `tools/data_collector.py` — 현장 학습 데이터 수집
- [ ] `src/activity_engine/model_engine.py` — TFLite 추론 구현
- [ ] `src/core/risk_scoring.py` — 위험도 산출 로직 구현
- [ ] `src/summary_engine/llama_cpp_wrapper.py` — sLLM 래퍼 구현
- [ ] `src/core/orchestrator.py` — 파이프라인 조율 구현
- [ ] `src/worker.py` — Redis 데몬 구현 (CNN 메인스레드 + LLM 데몬스레드)
- [ ] `tools/test_local.py` — 로컬 추론 테스트
