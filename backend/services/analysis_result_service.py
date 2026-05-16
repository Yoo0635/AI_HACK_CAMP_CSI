import json
import logging

from redis.exceptions import RedisError

from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_ANALYSIS_NAME
from backend.entities.bed import Bed
from backend.entities.analysis_result import AnalysisResult
from backend.exceptions.custom_exception import BedNotFoundByNodeException
from backend.repositories.analysis_result_repository import save_analysis_result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


class AnalysisResultSaveException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class AnalysisResultRedisSaveException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def save_analysis_result_db(
    db: Session,
    fields: dict[str, object],
    risk_scores: list[float] | None = None,
    secure_log: bytes | None = None,
) -> AnalysisResult:
    node_id = str(fields["node_id"])

    bed = db.query(Bed).filter(Bed.node_id == node_id).first()
    if bed is None:
        raise BedNotFoundByNodeException(node_id)

    sllm_summary = str(fields.get("sllm_summary", "none"))
    sllm_timestamp = int(fields.get("sllm_timestamp", 0))

    if secure_log is None:
        if risk_scores is None:
            risk_scores = [float(fields["risk_score"])]

    try:
        analysis_result = save_analysis_result(
            db=db,
            bed_id=bed.id,
            secure_log=risk_scores,
            sllm_summary=sllm_summary,
            sllm_timestamp=sllm_timestamp,
        )
    except SQLAlchemyError as exc:
        logger.exception(
            "분석 결과 DB 저장에 실패했습니다. node_id=%s",
            node_id,
        )
        raise AnalysisResultSaveException(
            f"분석 결과 DB 저장에 실패했습니다. node_id={node_id}"
        ) from exc

    return analysis_result


def save_analysis_result_redis(fields: dict[str, object]) -> str:
    node_id = str(fields["node_id"])
    seq_num = int(fields["seq_num"])
    label = str(fields["label"])
    cnn_score = float(fields["cnn_score"])
    energy = float(fields["energy"])
    is_anomaly = bool(fields["is_anomaly"])
    cnn_timestamp = int(fields["cnn_timestamp"])
    risk_score = float(fields["risk_score"])

    try:
        message_id = redis_client.xadd(
            CSI_ANALYSIS_NAME,
            {
                "node_id": node_id,
                "seq_num": seq_num,
                "label": label,
                "cnn_score": cnn_score,
                "energy": energy,
                "is_anomaly": json.dumps(is_anomaly),
                "cnn_timestamp": cnn_timestamp,
                "risk_score": risk_score,
            },
            maxlen=600,
            approximate=True,
        )
    except RedisError as exc:
        logger.exception(
            "분석 결과 Redis Stream 저장에 실패했습니다. node_id=%s seq_num=%s",
            node_id,
            seq_num,
        )
        raise AnalysisResultRedisSaveException(
            "분석 결과 Redis Stream 저장에 실패했습니다. "
            f"node_id={node_id} seq_num={seq_num}"
        ) from exc

    logger.info(
        "csi_analysis_stream 저장 완료 message_id=%s node_id=%s seq_num=%s label=%s risk_score=%s energy=%s is_anomaly=%s",
        message_id,
        node_id,
        seq_num,
        label,
        risk_score,
        energy,
        is_anomaly,
    )

    return str(message_id)
