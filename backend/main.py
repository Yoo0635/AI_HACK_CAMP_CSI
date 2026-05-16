import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.controllers.bed_controller import bed_router
from backend.controllers.csi_controller import csi_router
from backend.controllers.csi_ws_controller import ws_router
from backend.config.database import Base, engine
from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_LOG_NAME
from backend.exceptions.global_handler import register_exception_handlers
from backend.workers.sllm_worker import run_sllm_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=run_sllm_worker, daemon=True)
    t.start()
    yield


app = FastAPI(lifespan=lifespan)

# 👇 프론트엔드(React/Vite)가 접근할 수 있도록 CORS 통과 설정 추가!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 주소(포트)에서의 요청 허용 (테스트용)
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE 등 모든 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

redis_client.delete(CSI_LOG_NAME)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

register_exception_handlers(app)

app.include_router(bed_router)
app.include_router(csi_router)
app.include_router(ws_router)


@app.get("/")
def health() -> dict[str, str]:
    return {"message": "Hello World"}
