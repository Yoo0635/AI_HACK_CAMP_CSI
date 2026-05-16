# 개발 로그
## 2026-05-16

**11시**
- .gitignore, .dockerignore 작성 docker-compose.yml에 redis, FastAPI, PostgreSQL 등록
- Backend Directory Structure 생성
- 가상환경에 pip install 완료 및 인터프리터 설정
- main.py 테스트

**13시**
- .env, .env.docker 
- PostgreSQL Config 
- Global Custom Exception Handler
- POST /beds API (beds-service-DTO-controller)
- PostgreSQL에 bed 정보 저장
- GET /beds API (beds-service-DTO-controller)
- Redis Config

**14시**
- redis async config, redis_stream name
- POST /csi/raw (service-DTO-controller)
- redis stream에 CSI 데이터 저장
- redis stream에 CNN 분석 데이터 저장 창구 만들기 (service-DTO-CNN_worker)
- PostgreSQL에 SLLM 분석 데이터 저장 창구 만들기 (repository-service-DTO-SLLM_worker)

**15시**
- CNN Worker, CNN Analysis Model 생성
- Gorilla 압축, Fernet 암호화

**16시**
- risk_score_scure_service 
- analysis result service에 risk score 암호화, 압축 연동
- SLLM Worker 생성
- WebSocket /ws/csi/{node_id} (service-DTO-controller)