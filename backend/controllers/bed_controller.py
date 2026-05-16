from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config.database import get_db
from backend.schemas.request.bed_request import BedCreateRequest
from backend.services.bed_service import create_bed

bed_router = APIRouter()


@bed_router.post("/beds", status_code=201)
def create_bed_api(
    request: BedCreateRequest,
    db: Session = Depends(get_db),
) -> None:
    create_bed(request, db)
    return