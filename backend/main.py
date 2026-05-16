from fastapi import FastAPI

from backend.config.database import Base, engine
from backend.controllers.bed_controller import bed_router
from backend.exceptions.global_handler import register_exception_handlers

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()

register_exception_handlers(app)

app.include_router(bed_router)

@app.get("/")
async def root():
    return "Hello World"