# AI_HACK_CAMP_CSI

CSI(Channel State Information) 데이터를 활용해 환자의 낙상·이상 행동을 감지하고 시각화하는 AI HACK CAMP 프로젝트입니다.

ESP32 센서가 수집한 Wi-Fi CSI 신호를 AI가 실시간 분석해 낙상을 감지하고, FastAPI 백엔드와 React 대시보드로 병상 상태를 모니터링합니다.

## 시스템 구조

```
ESP32 센서(NODE001 / NODE002)
    └─ Wi-Fi CSI 신호 수집
         └─ FastAPI  POST /csi/raw
              └─ Redis  csi_log_stream
                   └─ AI Worker (Raspberry Pi)
                        ├─ CNN 추론  →  NORMAL / MOVE / FALL
                        ├─ 듀얼센서 교차검증 (오탐 억제)
                        └─ Redis  csi_analysis_stream
                             └─ FastAPI WebSocket
                                  └─ React 대시보드
```

## 기술 스택

### Frontend
- React (Vite) / TypeScript
- Tailwind CSS v4
- React Icons

### Backend
- Python 3.11 / FastAPI / SQLAlchemy
- PostgreSQL / Redis
- Docker Compose

### AI (Raspberry Pi ARM64)
- TFLite INT8 — CNN 낙상 분류
- llama.cpp / EXAONE 3.5 2.4B — 한국어 상황 요약 (sLLM)
- Redis Streams

## 디렉터리 구조

```text
.
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── config/
│   ├── controllers/
│   ├── entities/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── ai/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── models/
│   │   ├── activity_cnn_int8.tflite   # 낙상 감지 CNN
│   │   ├── sllm_model.gguf            # EXAONE sLLM (별도 다운로드)
│   │   └── download_models.sh
│   ├── src/
│   │   ├── worker.py                  # 메인 실행 (CNN + LLM 2스레드)
│   │   ├── config.py
│   │   ├── core/
│   │   │   ├── orchestrator.py        # 파이프라인 조율 + 듀얼센서 검증
│   │   │   └── risk_scoring.py
│   │   ├── activity_engine/
│   │   │   ├── model_engine.py        # TFLite 추론
│   │   │   └── preprocessing.py      # 슬라이딩 윈도우 전처리
│   │   └── summary_engine/
│   │       └── llama_cpp_wrapper.py
│   └── tools/
│       ├── train.py                   # CNN 학습 및 TFLite 변환
│       ├── data_collector.py          # 현장 데이터 수집
│       ├── eval_model.py
│       └── test_local.py
├── docker-compose.yml
└── DevLog_Backend.md
```

## 실행 방법

### 전체 실행 순서

**1. AI Worker (Raspberry Pi)**

```bash
cd ai
docker build -t csi-ai .
docker run -d --name csi-ai-worker --network host csi-ai
```

> sLLM 모델이 없으면 더미 모드로 동작합니다. 필요 시 아래 다운로드 참고.

**2. Backend + 인프라 (Docker Compose)**

```bash
docker compose up --build
```

- API 서버: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

**3. Frontend**

```bash
cd frontend
npm install
npm run dev
```

- 대시보드: `http://localhost:5173`

---

### 개별 로컬 실행

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## 환경 변수

### Backend

```env
DATABASE_URL=postgresql+psycopg2://user:1234@localhost:5432/csi_db
REDIS_HOST=localhost
REDIS_PORT=6379
```

### AI

```env
REDIS_HOST=localhost
REDIS_PORT=6379
CSI_STREAM_NAME=csi_log_stream
TFLITE_MODEL_PATH=models/activity_cnn_int8.tflite
GGUF_MODEL_PATH=models/sllm_model.gguf
```

## AI 모듈 상세

### 처리 흐름

```
csi_log_stream
  └─ CNN 루프 (메인 스레드)
       ├─ 20샘플 슬라이딩 윈도우 → (1, 20, 64, 2)
       ├─ TFLite 추론 → NORMAL / MOVE / FALL
       ├─ 듀얼센서 검증 (NODE002 움직임 확인 시만 FALL 확정)
       └─ csi_analysis_stream xadd

csi_analysis_stream
  └─ LLM 스레드 (데몬)
       └─ is_anomaly == true 시 EXAONE 한국어 요약 → xadd
```

### 분류 클래스 및 위험도

| 클래스 | 설명 | 기본 점수 |
|--------|------|-----------|
| NORMAL | 정지 상태 | 20점 |
| MOVE | 움직임 | 65점 |
| FALL | 낙상 | 85점 |

```
risk_score = 기본점수 × CNN 신뢰도 + 에너지 보정 (최대 15점)
is_anomaly = risk_score > 43
```

### 듀얼센서 낙상 검증

```
CNN(NODE001)이 FALL 감지
    ├─ NODE002 최근 5초 움직임 확인 → FALL 확정
    └─ NODE002 움직임 없음 / 데이터 부족 → MOVE 재분류 (오탐 억제)
```

### CNN 모델 정보

| 항목 | 내용 |
|------|------|
| 입력 | (1, 20, 64, 2) — 20프레임 × 64 서브캐리어 × 2채널 |
| 출력 | 3클래스 softmax |
| FALL recall | 100% (w_fall=8.0 재훈련) |
| 크기 | ~163 KB (INT8 양자화) |

### sLLM 모델 다운로드

```bash
pip install huggingface_hub
huggingface-cli download \
  bartowski/EXAONE-3.5-2.4B-Instruct-GGUF \
  EXAONE-3.5-2.4B-Instruct-Q4_K_M.gguf \
  --local-dir ai/models/ \
  --local-dir-use-symlinks False

mv ai/models/EXAONE-3.5-2.4B-Instruct-Q4_K_M.gguf ai/models/sllm_model.gguf
```

## API

### `GET /`
서버 상태 확인. 응답: `"Hello World"`

### `POST /beds`
병상 등록.

```json
{
  "bed_id": "BED-001",
  "node_id": "NODE001",
  "nickname": "patient-a",
  "age": 72,
  "disease": "hypertension"
}
```

### `GET /beds`
병상 목록 조회.

## 주의사항

- `backend/main.py` 시작 시 테이블 drop/create 실행 — 운영 환경에서는 제거 필요
- `sllm_model.gguf` (~1.7 GB)은 저장소 미포함, 별도 다운로드 필요
- CSI 패턴은 센서 위치·공간 구조에 따라 달라지므로 환경 변경 시 데이터 재수집 및 재학습 필요

## 문서

- [DevLog_Backend.md](DevLog_Backend.md)
