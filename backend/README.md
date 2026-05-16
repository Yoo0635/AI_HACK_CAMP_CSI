# AI_HACK_CAMP_CSI

CSI(Channel State Information) 데이터를 활용해 환자의 이상 행동을 감지하고 시각화하는 AI HACK CAMP 프로젝트입니다. 프론트엔드 대시보드와 FastAPI 백엔드를 함께 포함하고 있습니다.

## 개요

- 실시간 웹소켓 기반 환자 모니터링 대시보드
- 병상(Node) 단위 위험도 수신 및 시각화
- CSI 분석 결과를 활용한 이상 행동 탐지 파이프라인

## 기술 스택

### Frontend

- React (Vite)
- TypeScript
- Tailwind CSS v4
- React Icons

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker Compose

## 주요 기능

- 실시간 웹소켓 통신으로 각 병상(Node)의 Risk Score 수신
- 시간 흐름에 따른 상태 변화 그래프 시각화
- 위험 수치 임계값 도달 시 경고성 UI 표시
- 병상 관리 인터페이스와 데이터 조회 기능
- `beds` 도메인 등록/조회 API

## 디렉터리 구조

```text
.
├── backend
│   ├── config
│   ├── controllers
│   ├── entities
│   ├── exceptions
│   ├── repositories
│   ├── schemas
│   ├── services
│   ├── utils
│   ├── workers
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend
│   ├── public
│   ├── src
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── DevLog_Backend.md
```

## 실행 전 환경 변수

로컬 실행 또는 Docker 실행 전 아래 환경 변수가 필요합니다.

```env
DATABASE_URL=
REDIS_HOST=
REDIS_PORT=
```

예시:

```env
DATABASE_URL=postgresql+psycopg2://user:1234@localhost:5432/csi_db
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 실행 방법

### 1. Docker Compose

```bash
docker compose up --build
```

기본 주소:

- API 서버: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### 2. 백엔드 로컬 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload
```

### 3. 프론트엔드 로컬 실행

```bash
cd frontend
npm install
npm run dev
```

## API

### `GET /`

- 서버 상태 확인용 기본 엔드포인트
- 응답: `"Hello World"`

### `POST /beds`

- 병상 정보를 등록합니다.

요청 예시:

```json
{
  "bed_id": "BED-001",
  "node_id": "NODE-001",
  "nickname": "patient-a",
  "age": 72,
  "disease": "hypertension"
}
```

유효성 조건:

- `bed_id`, `node_id`: 1~50자
- `nickname`: 1~100자
- `age`: 0~150
- `disease`: 1~200자
- 문자열 필드는 공백만 입력할 수 없음

### `GET /beds`

- 등록된 병상 목록을 조회합니다.

## 개발 로그

- 13:00 react 필요 UI 요소 설치
- 13:32 해더 제작
- 14:00 사이드바 제작
- 14:28 환자 카드 제작
- 14:43 상태 확인 카드 제작
- 17:20 도커 연결
- 18:38 웹소켓 구현
- 19:33 웹소켓 오류 완전 해결
- 19:33위험 발생 시 대시보드 전체 알림 시스템 구축

## 다음 작업

- 사용자가 보기 쉽게 대시보드 꾸미기
- 백엔드 AI 모델 분석 결과와 프론트엔드 최종 연동 테스트

## 주의사항

`backend/main.py`에서 앱 시작 시 아래 로직이 실행됩니다.

- `Base.metadata.drop_all(bind=engine)`
- `Base.metadata.create_all(bind=engine)`

개발 환경에서는 편하지만 서버 재시작 시 테이블이 초기화될 수 있습니다. 운영 환경에서는 제거하거나 마이그레이션 도구로 대체하는 편이 안전합니다.

## 문서

- [DevLog_Backend.md](DevLog_Backend.md)
