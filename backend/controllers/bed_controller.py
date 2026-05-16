from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config.database import get_db
from backend.schemas.request.bed_request import BedCreateRequest
from backend.schemas.response.bed_response import BedsResponse
from backend.services.bed_service import create_bed, get_beds

bed_router = APIRouter()


@bed_router.post("/beds", status_code=201)
def create_bed_api(
    request: BedCreateRequest,
    db: Session = Depends(get_db),
) -> None:
    create_bed(request, db)
    return

@bed_router.get("/beds", status_code=200, response_model=BedsResponse)
def get_beds_api(
    db: Session = Depends(get_db),
) -> BedsResponse:
    return get_beds(db)