import logging

from fastapi import WebSocket
from redis.exceptions import RedisError

from backend.config.redis_async import redis_async_client
from backend.config.redis_streams import CSI_ANALYSIS_NAME
from backend.exceptions.custom_exception import (
    WebSocketStreamReadException,
)
from backend.schemas.response.csi_ws_response import (
    RiskScoreResponse,
)

logger = logging.getLogger(__name__)


async def stream_risk_score(
    ws: WebSocket,
    node_id: str,
) -> None:
    last_id = "$"

    while True:
        try:
            messages = await redis_async_client.xread(
                streams={CSI_ANALYSIS_NAME: last_id},
                count=1,
                block=3000,
            )
        except RedisError as exc:
            raise WebSocketStreamReadException(CSI_ANALYSIS_NAME) from exc

        if not messages:
            continue
        for _, stream_messages in messages:
            for message_id, fields in stream_messages:
                last_id = message_id

                try:
                    stream_node_id = str(fields["node_id"])
                    risk_score = float(fields["risk_score"])
                except (KeyError, TypeError, ValueError):
                    logger.exception(
                        "실시간 위험도 메시지 파싱에 실패했습니다. message_id=%s fields=%s",
                        message_id,
                        fields,
                    )
                    continue

                if stream_node_id != node_id:
                    continue
                response = RiskScoreResponse(
                    node_id=stream_node_id,
                    risk_score=risk_score,
                )
                await ws.send_json(response.model_dump())