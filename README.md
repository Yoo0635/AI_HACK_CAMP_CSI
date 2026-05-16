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

### 데이터 수집

먼저 실행 → 그 다음 동작 재현 (수집기가 돌아가는 동안 행동):

```bash
python tools/data_collector.py --label NORMAL --duration 3
python tools/data_collector.py --label MOVE   --duration 3
python tools/data_collector.py --label FALL   --duration 3
```

#### 학습 목표 샘플 수

3초 수집 1회 = 약 60개 raw 샘플 (20패킷/초 × 3초)

| 클래스 | 최소 수집 횟수 | 목표 샘플 수 | 비고 |
|--------|--------------|-------------|------|
| NORMAL | 50회 이상 | 3,000개+ | 정지 상태 다양한 자세 |
| MOVE | 50회 이상 | 3,000개+ | 뒤척임·움직임 반복 |
| FALL | 30회 이상 | 1,800개+ | 침대 이탈 동작 반복 재현 |

> 현장 환경이 바뀌면 반드시 해당 환경에서 재수집 후 재학습 — CSI 패턴은 센서 위치·공간 구조에 따라 크게 달라짐

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

**14:30** — `tools/data_collector.py` 구현 완료 (현장 세팅 완료)
- `--label NORMAL / MOVE / FALL` CLI 인자로 레이블 지정
- `--duration` 초 동안 `csi_log_stream` 구독 후 `.npy` 저장
- 파일명: `{LABEL}_{timestamp}_{n}samples.npy`

**15:30** — 버그 수정
- `src/config.py`: `REDIS_URL` → `REDIS_HOST` / `REDIS_PORT` 분리, 스트림명 `CsiLogStream` → `csi_log_stream` 수정
- `tools/data_collector.py`: `xread count=10` → `count=100` (수집 누락 방지)

**16:00~19:00** — 현장 학습 데이터 수집 완료
- NORMAL: 3,669개 (목표 3,000 달성)
- MOVE: 3,255개 (목표 3,000 달성)
- FALL: 1,806개 (목표 1,800 달성)

**19:00** — `tools/train.py` 구현 완료
- 파일 단위 슬라이딩 윈도우(20프레임) 생성
- 서브캐리어 32 DC null 선형 보간 (`arr[:, 32] = (arr[:, 31] + arr[:, 33]) / 2.0`)
- amplitude + Doppler 2채널 전처리 → (N, 20, 64, 2)
- Conv2D×2 → LSTM(64) → Dense(3) softmax 모델
- 클래스 불균형 가중치 자동 적용 (compute_class_weight)
- TFLite INT8 양자화 변환 → `models/activity_cnn_int8.tflite`

**19:40** — 학습 중 과적합 발견 및 데이터 분할·모델 수정
- 문제 1: 윈도우 단위 random split → 인접 윈도우(19프레임 겹침)가 train/val 양쪽에 분포 → val_accuracy 허위 100%
- 문제 2: 파일 단위 분할 시 NORMAL 파일 2개뿐 → 실제 과적합 확인 (val 22%까지 하락)
- 수정 1: 청크(150프레임) 단위 분할 → 파일 수가 적어도 다양한 분할 가능
- 수정 2: 모델 정규화 강화 — Conv 필터 32→16/64→32, LSTM 64→32, Dropout 추가, L2 정규화 적용
- 결과: val_accuracy 99.77% (에폭 9, EarlyStopping)

**20:00** — TFLite 변환 오류 수정 및 학습 완료
- 오류: `LSTM`의 내부 루프(`TensorListReserve`)가 TFLite 빌트인 미지원
- 수정: `LSTM(32, unroll=True)` — 루프를 20단계 정적으로 펼쳐 TFLite 호환
- 최종 결과: val_accuracy 100%, val_loss 0.0241 (에폭 13, EarlyStopping)
- TFLite INT8 변환 완료: `models/activity_cnn_int8.tflite` (171.9 KB)

**20:10** — `src/activity_engine/model_engine.py` 구현 완료
- TFLite 모델 로드 및 추론 (`tflite_runtime`)
- `predict(window)` → `(label, confidence, energy)` 반환
- energy: amplitude 채널 평균 제곱값 (위험도 보정용)

**20:15**— `src/core/risk_scoring.py` 구현 완료
- `risk_score = 기본점수 × confidence + 에너지 보정 (최대 15점)`
- `is_anomaly = risk_score > 43`
- 기본점수: NORMAL 20 / MOVE 65 / FALL 85 (상수로 분리, 테스트 후 조정 가능)

**20:20** — `src/core/orchestrator.py` 구현 완료
- `process(node_id, seq_num, csi_matrix)` → Preprocessor → ActivityEngine → compute_risk → xadd
- 윈도우 미달 시 False 반환 (20프레임 쌓일 때까지 스킵)
- `csi_analysis_stream` xadd (maxlen=600)

---

**20:30** — `src/summary_engine/llama_cpp_wrapper.py` 구현 완료
- EXAONE GGUF 모델 로드 (`llama_cpp`, n_ctx=512, n_threads=4)
- `summarize(label, cnn_score, risk_score, energy)` → 한국어 2문장 요약
- 프롬프트: 감지 상태·신뢰도·위험지수·에너지 → temperature=0.3, max_tokens=128

---

**20:40** — `src/worker.py` 구현 완료
- CNN 메인 루프: `csi_log_stream` xread → `orchestrator.process()`
- LLM 데몬 스레드: `csi_analysis_stream` xread → `is_anomaly==true` 시 `summary_engine.summarize()` → xadd
- LLM 스레드는 `daemon=True`로 CNN 루프 종료 시 자동 종료

---

**21:00** — `tools/test_local.py` 구현 완료
- `--mode pipeline`: Orchestrator 직접 호출 (Redis 없이 파이프라인 동작 확인)
- `--mode inject`: Redis에 더미 CSI 프레임 주입
- `--mode read`: `csi_analysis_stream` 최근 결과 출력

---

### 2026-05-17

**Windows 호환성 수정 (`model_engine.py`, `llama_cpp_wrapper.py`)**
- `tflite_runtime` Windows 미지원 → try/except로 `tensorflow.lite` fallback 추가
- `llama_cpp` Windows 미설치 시 더미 모드로 폴백 (실제 추론 없이 레이블 반환)
  - 더미 출력: `[더미] {label} 감지 (score={cnn_score:.1%}, risk={risk_score:.1f})`
- 두 수정 모두 Pi 배포에는 영향 없음 (llama_cpp, tflite_runtime 정상 설치됨)

**라즈베리파이 배포 완료**
- SSH 설정: `csi@192.168.1.2` (SSH 키 등록으로 비밀번호 없이 접속)
- `deploy/backend/docker-compose.yml`에 `ai-worker` 서비스 추가
  - Redis healthcheck 의존, `../ai/models:/app/models` 볼륨 마운트
- 기존 포트 충돌(6379) → 구 컨테이너 전부 정리 후 재기동
- sLLM 모델 Pi에 직접 다운로드 (huggingface-cli, EXAONE Q4_K_M, ~1.7 GB)
- Pi `~/csi/ai/data/` 권한 문제 (Docker가 root로 생성) → `chown -R csi:csi` 처리

**데이터 추가 수집**
- FALL·MOVE 현장 추가 수집 (Pi에서 `data_collector.py` 직접 실행)
- NORMAL 파일 교체: 대용량 2개(1,222+2,447 samples) → 균일 크기 10개(각 ~455 samples)
  - 파일 크기 편차 완화로 청크 분할 균형 개선

**`tools/train.py` 개선**
- `sklearn.metrics.confusion_matrix` 기반 클래스별 정확도·혼동 행렬 출력 추가
- 수동 클래스 가중치 CLI 인자 추가: `--w_normal`, `--w_move`, `--w_fall`
  - 미설정 시 `compute_class_weight("balanced", ...)` 자동 계산 유지

**클래스 가중치 튜닝 이력**

자동 가중치로 MOVE 25.6% → 수동 조정 반복:

| 실험 | --w_normal | --w_move | --w_fall | NORMAL | MOVE | FALL | 비고 |
|------|-----------|---------|---------|--------|------|------|------|
| 자동 | (auto) | (auto) | (auto) | 100% | 25.6% | 100% | MOVE 미분류 |
| 1차 | 0.3 | 5.0 | 6.0 | 100% | 84.3% | 84.4% | FALL 오탐 다수 |
| 2차 | 0.2 | 4.0 | 9.0 | — | — | — | FALL 오탐 과다 |
| 3차 | 0.3 | 4.0 | 6.0 | 100% | 87.1% | 100% | val_acc 94.98% |
| 최종 | 0.3 | 4.0 | 6.0 | **100%** | **100%** | **98.4%** | 새 NORMAL 데이터 재학습 |

> 최종 학습 (2026-05-17): val_accuracy 0.9980, 14 에폭(EarlyStopping), 171.9 KB

**도메인 과적합 이슈 파악 및 대응**
- 현상: val_accuracy 99%+이지만 실제 환경에서 NORMAL을 MOVE/FALL로 오분류
- 원인: 센서 위치·공간 구조가 CSI 패턴을 결정 → 훈련 환경 특성을 모델이 암기
- 대응: 동일 환경에서 NORMAL 추가 수집 → 현재 환경의 정지 CSI 패턴 반영
- 근본 해결책: 배포 환경에서 데이터 재수집 후 재학습 필수

---

## 다음 작업

- [ ] Pi에 새 모델 배포 후 실환경 테스트 (`scp` → `docker compose restart ai-worker`)
- [ ] NORMAL 누운 자세 데이터 추가 수집 (오탐 개선 시 재학습)
