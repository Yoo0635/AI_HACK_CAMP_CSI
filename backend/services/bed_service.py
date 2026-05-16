from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.entities.bed import Bed
from backend.exceptions.custom_exception import (
    BedCreateException,
    BedQueryException,
    DuplicateBedException,
)
from backend.schemas.request.bed_request import BedCreateRequest


def create_bed(request: BedCreateRequest, db: Session) -> None:
    bed = Bed(
        bed_id=request.bed_id,
        node_id=request.node_id,
        nickname=request.nickname,
        age=request.age,
        disease=request.disease,
    )

    try:
        db.add(bed)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        error_text = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()

        if "beds.bed_id" in error_text:
            raise DuplicateBedException("bed_id", request.bed_id) from exc

        if "beds.node_id" in error_text:
            raise DuplicateBedException("node_id", request.node_id) from exc

        raise DuplicateBedException("bed_id 또는 node_id", request.bed_id) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise BedCreateException() from exc


def get_beds(db: Session) -> dict[str, list[Bed]]:
    try:
        beds = db.query(Bed).all()
    except SQLAlchemyError as exc:
        raise BedQueryException() from exc

    return {"beds": beds}
