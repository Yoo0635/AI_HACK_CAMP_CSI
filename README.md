# CSI Deploy — 로컬 현장 실행 환경

## 개요

현장 데이터 수집 및 통합 테스트를 위한 로컬 실행 환경.
백엔드(FastAPI + PostgreSQL + Redis)와 AI Worker를 노트북에서 함께 구동한다.

---

## 설명

### 구성

```
deploy/
├── backend/          # FastAPI + PostgreSQL + Redis (docker-compose)
│   ├── docker-compose.yml
│   └── backend/      # FastAPI 앱 소스
└── ai/               # AI Worker (data_collector, worker 등)
    ├── src/
    └── tools/
```

### 실행 순서

**1. 백엔드 실행 (Docker)**

```bash
cd deploy/backend
docker-compose up -d
```

| 서비스 | 포트 | 설명 |
|--------|------|------|
| FastAPI | 8000 | ESP32 CSI 수신 엔드포인트 |
| PostgreSQL | 5432 | 분석 결과 저장 |
| Redis | 6379 | csi_log_stream / csi_analysis_stream |

**2. 데이터 수집**

```bash
cd deploy/ai
pip install -r requirements.txt

# 먼저 실행 → 그 다음 동작 재현 (수집기가 돌아가는 동안 행동)
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

**3. ESP32 설정**

`firmware/include/config.h` 의 `FASTAPI_URL`을 노트북 IP로 설정:

```
FASTAPI_URL = "http://<노트북_IP>:8000/csi/log"
```

---

## 개발 로그

### 2026-05-16

**14:50** — 현장 deploy 환경 구성
- `backend/` — FastAPI + PostgreSQL + Redis (docker-compose)
- `ai/` — AI Worker 소스 클론

---

## 다음 작업

- [ ] `docker-compose up` 백엔드 정상 기동 확인
- [ ] ESP32 연결 및 `csi_log_stream` 수신 확인
- [ ] 현장 데이터 수집 (NORMAL / MOVE / FALL)
