import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.exceptions.custom_exception import WebSocketAppException
from backend.schemas.response.csi_ws_response import WebSocketErrorResponse
from backend.services.csi_ws_service import stream_risk_score

ws_router = APIRouter()
logger = logging.getLogger(__name__)


async def send_websocket_error(
    ws: WebSocket,
    exc: WebSocketAppException,
) -> None:
    await ws.send_json(
        WebSocketErrorResponse(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        ).model_dump()
    )
    await ws.close(code=exc.close_code)


@ws_router.websocket("/ws/csi/{node_id}")
async def ws_csi_risk_score_api(
    ws: WebSocket,
    node_id: str,
) -> None:
    await ws.accept()

    try:
        await stream_risk_score(ws, node_id)
    except WebSocketDisconnect:
        logger.info("websocket disconnected: node_id=%s", node_id)
    except WebSocketAppException as exc:
        logger.exception(
            "실시간 위험도 websocket 처리에 실패했습니다. node_id=%s error_code=%s",
            node_id,
            exc.error_code,
        )
        await send_websocket_error(ws, exc)
    except Exception:
        logger.exception(
            "실시간 위험도 websocket 처리 중 알 수 없는 오류가 발생했습니다. node_id=%s",
            node_id,
        )
        await send_websocket_error(
            ws,
            WebSocketAppException(
                message="실시간 위험도 스트리밍 중 알 수 없는 오류가 발생했습니다.",
                error_code="WS_INTERNAL_SERVER_ERROR",
            ),
        )