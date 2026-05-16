import logging

from fastapi import WebSocket
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config.redis_async import redis_async_client
from backend.config.redis_streams import CSI_ANALYSIS_NAME
from backend.entities.analysis_result import AnalysisResult
from backend.entities.bed import Bed
from backend.exceptions.custom_exception import (
    WebSocketDatabaseException,
    WebSocketStreamReadException,
)
from backend.schemas.response.csi_ws_response import (
    AlertRiskScoreResponse,
    InitAlertResponse,
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


async def stream_alert(
    ws: WebSocket,
    db: Session,
) -> None:
    last_id = "$"
    alert_started = False

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
                    risk_score = float(fields["risk_score"])
                    is_anomaly = str(fields["is_anomaly"]).lower() == "true"
                    stream_node_id = str(fields["node_id"])
                    label = str(fields["label"])
                    cnn_timestamp = int(fields["cnn_timestamp"])
                except (KeyError, TypeError, ValueError):
                    logger.exception(
                        "실시간 알림 메시지 파싱에 실패했습니다. message_id=%s fields=%s",
                        message_id,
                        fields,
                    )
                    continue

                if not alert_started and not is_anomaly:
                    continue

                if not alert_started and is_anomaly:
                    try:
                        bed = db.query(Bed).filter(Bed.node_id == stream_node_id).first()
                    except SQLAlchemyError as exc:
                        raise WebSocketDatabaseException("침대 조회") from exc

                    if bed is None:
                        logger.warning(
                            "알림 대상 침대를 찾지 못해 메시지를 건너뜁니다. node_id=%s message_id=%s",
                            stream_node_id,
                            message_id,
                        )
                        continue

                    try:
                        latest_result = (
                            db.query(AnalysisResult)
                            .filter(AnalysisResult.bed_id == bed.id)
                            .order_by(AnalysisResult.id.desc())
                            .first()
                        )
                    except SQLAlchemyError as exc:
                        raise WebSocketDatabaseException("최근 분석 결과 조회") from exc

                    await ws.send_json(
                        InitAlertResponse(
                            bed_id=bed.bed_id,
                            nickname=bed.nickname,
                            label=label,
                            cnn_timestamp=cnn_timestamp,
                            sllm_summary=(
                                latest_result.sllm_summary
                                if latest_result is not None
                                else "none"
                            ),
                            risk_score=risk_score,
                        ).model_dump()
                    )

                    alert_started = True
                    continue

                await ws.send_json(
                    AlertRiskScoreResponse(
                        risk_score=risk_score,
                    ).model_dump()
                )
