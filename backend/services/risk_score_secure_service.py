import logging

from redis.exceptions import RedisError

from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_ANALYSIS_NAME
from backend.services.analysis_result_service import save_analysis_result_db
from backend.utils.fernet_crypto import encrypt_bytes
from backend.utils.gorilla_compressor import compress_risk_scores
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)

RISK_SCORE_WINDOW_SIZE = 300
RISK_SCORE_MAX_COUNT = 600


class RedisRiskScoreFetchException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class GorillaCompressionException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class FernetEncryptionException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def store_secure_risk_scores(
    db: Session,
    fields: dict,
    trigger_message_id: str,
):
    node_id = str(fields["node_id"])

    risk_scores = fetch_risk_scores_for_trigger(
        node_id=node_id,
        trigger_message_id=trigger_message_id,
    )

    logger.info(
        "압축 전 risk_score 개수 node_id=%s count=%s",
        node_id,
        len(risk_scores),
    )

    if len(risk_scores) < RISK_SCORE_MAX_COUNT:
        logger.info(
            "최대 수집 개수보다 적은 risk_score를 저장합니다. node_id=%s count=%s",
            node_id,
            len(risk_scores),
        )

    compressed_bytes = compress_risk_score_bytes(
        node_id=node_id,
        risk_scores=risk_scores,
    )
    encrypted_bytes = encrypt_risk_score_bytes(
        node_id=node_id,
        compressed_bytes=compressed_bytes,
    )

    return save_analysis_result_db(
        db=db,
        fields=fields,
        secure_log=encrypted_bytes,
    )


def fetch_risk_scores_for_trigger(
    node_id: str,
    trigger_message_id: str,
) -> list[float]:
    try:
        stream_entries = redis_client.xrange(
            CSI_ANALYSIS_NAME,
            min="-",
            max="+",
            count=RISK_SCORE_MAX_COUNT,
        )
    except RedisError as exc:
        raise RedisRiskScoreFetchException(
            f"Redis에서 risk_score 조회에 실패했습니다. node_id={node_id}"
        ) from exc

    node_entries = [
        (message_id, entry_fields)
        for message_id, entry_fields in stream_entries
        if str(entry_fields.get("node_id")) == node_id
    ]

    trigger_index = next(
        (
            index
            for index, (message_id, _) in enumerate(node_entries)
            if message_id == trigger_message_id
        ),
        -1,
    )

    if trigger_index < 0:
        raise RedisRiskScoreFetchException(
            "Redis Stream에서 트리거 메시지를 찾지 못했습니다. "
            f"node_id={node_id} message_id={trigger_message_id}"
        )

    previous_entries = node_entries[
        max(trigger_index - RISK_SCORE_WINDOW_SIZE, 0):trigger_index
    ]
    next_entries = node_entries[
        trigger_index + 1:trigger_index + 1 + RISK_SCORE_WINDOW_SIZE
    ]
    collected_entries = previous_entries + next_entries

    logger.info(
        "risk_score 수집 완료 node_id=%s trigger_message_id=%s 이전=%s 이후=%s 전체=%s 첫값=%s 마지막값=%s",
        node_id,
        trigger_message_id,
        len(previous_entries),
        len(next_entries),
        len(collected_entries),
        collected_entries[0][1]["risk_score"] if collected_entries else None,
        collected_entries[-1][1]["risk_score"] if collected_entries else None,
    )

    return [
        float(entry_fields["risk_score"])
        for _, entry_fields in collected_entries
    ]


def compress_risk_score_bytes(
    node_id: str,
    risk_scores: list[float],
) -> bytes:
    try:
        compressed_bytes = compress_risk_scores(risk_scores)
    except Exception as exc:
        raise GorillaCompressionException(
            f"Gorilla 압축에 실패했습니다. node_id={node_id}"
        ) from exc

    logger.info(
        "Gorilla 압축 완료 node_id=%s compressed_bytes=%s",
        node_id,
        len(compressed_bytes),
    )

    return compressed_bytes


def encrypt_risk_score_bytes(
    node_id: str,
    compressed_bytes: bytes,
) -> bytes:
    try:
        encrypted_bytes = encrypt_bytes(compressed_bytes)
    except Exception as exc:
        raise FernetEncryptionException(
            f"Fernet 암호화에 실패했습니다. node_id={node_id}"
        ) from exc

    logger.info(
        "Fernet 암호화 완료 node_id=%s encrypted_bytes=%s",
        node_id,
        len(encrypted_bytes),
    )

    return encrypted_bytes
