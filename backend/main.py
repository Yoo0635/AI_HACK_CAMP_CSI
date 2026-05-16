from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 👉 CORS 미들웨어 추가!

from backend.controllers.bed_controller import bed_router
from backend.controllers.csi_controller import csi_router
from backend.controllers.csi_ws_controller import ws_router
from backend.config.database import Base, engine
from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_LOG_NAME
from backend.exceptions.global_handler import register_exception_handlers

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
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
