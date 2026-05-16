from fastapi import APIRouter
from fastapi import Request

from backend.schemas.response.csi_response import CsiRawResponse
from backend.services.csi_service import process_csi_raw_data

csi_router = APIRouter()


@csi_router.post(
    "/csi/raw",
    status_code=200,
    response_model=CsiRawResponse,
)
async def create_csi_raw_api(request: Request) -> CsiRawResponse:
    body = await request.body()
    response = process_csi_raw_data(body)

    return response
