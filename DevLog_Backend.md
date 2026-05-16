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
- POST /csi/raw (analysis_result-service-DTO-controller)
- redis에 CSI 데이터 저장