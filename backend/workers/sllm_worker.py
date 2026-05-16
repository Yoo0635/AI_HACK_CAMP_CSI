import logging
import time

from redis.exceptions import RedisError

from backend.config.database import SessionLocal
from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_ANALYSIS_NAME
from backend.services.analysis_result_service import AnalysisResultSaveException
from backend.services.risk_score_secure_service import (
    FernetEncryptionException,
    GorillaCompressionException,
    RedisRiskScoreFetchException,
    store_secure_risk_scores,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def create_sllm_summary(fields: dict) -> str:
    label = str(fields["label"])
    risk_score = float(fields["risk_score"])
    energy = float(fields["energy"])
    is_anomaly = fields["is_anomaly"]

    return (
        f"현재 상태는 {label}입니다. "
        f"위험 점수는 {risk_score}이고, "
        f"활동량 수치는 {energy}입니다. "
        f"이상 감지 여부는 {is_anomaly}입니다."
    )


COOLDOWN_SEC = 120


def run_sllm_worker() -> None:
    last_id = "$"
    last_summary_time: dict[str, float] = {}

    while True:
        try:
            stream_data = redis_client.xread(
                streams={CSI_ANALYSIS_NAME: last_id},
                count=1,
                block=1000,
            )
        except RedisError:
            logger.exception(
                "analysis stream 조회에 실패했습니다. stream=%s last_id=%s",
                CSI_ANALYSIS_NAME,
                last_id,
            )
            continue

        if not stream_data:
            continue

        for stream_name, messages in stream_data:
            for message_id, fields in messages:
                is_anomaly = str(fields.get("is_anomaly", "false")).lower() == "true"
                if not is_anomaly:
                    last_id = message_id
                    continue

                try:
                    risk_score_val = float(fields.get("risk_score", 0))
                except (ValueError, TypeError):
                    risk_score_val = 0.0
                if risk_score_val < 80.1:
                    last_id = message_id
                    continue

                node_id = str(fields.get("node_id", ""))
                now = time.time()
                if now - last_summary_time.get(node_id, 0) < COOLDOWN_SEC:
                    last_id = message_id
                    continue
                last_summary_time[node_id] = now

                try:
                    logger.info(
                        "SLLM worker 수신 message_id=%s node_id=%s label=%s risk_score=%s energy=%s is_anomaly=%s",
                        message_id,
                        fields.get("node_id"),
                        fields.get("label"),
                        fields.get("risk_score"),
                        fields.get("energy"),
                        fields.get("is_anomaly"),
                    )
                    sllm_summary = create_sllm_summary(fields)
                    fields["sllm_summary"] = sllm_summary
                    fields["sllm_timestamp"] = int(time.time())
                except (KeyError, ValueError, TypeError):
                    logger.exception(
                        "SLLM summary 생성에 실패했습니다. message_id=%s fields=%s",
                        message_id,
                        fields,
                    )
                    last_id = message_id
                    continue

                db = SessionLocal()
                save_succeeded = False

                try:
                    store_secure_risk_scores(
                        db=db,
                        fields=fields,
                        trigger_message_id=message_id,
                    )
                    db.commit()
                    save_succeeded = True
                except RedisRiskScoreFetchException as exc:
                    db.rollback()
                    logger.exception(
                        "Redis에서 risk_score 수집에 실패했습니다. node_id=%s message_id=%s error=%s",
                        fields.get("node_id"),
                        message_id,
                        exc,
                    )
                except GorillaCompressionException as exc:
                    db.rollback()
                    logger.exception(
                        "Gorilla 압축에 실패했습니다. node_id=%s message_id=%s error=%s",
                        fields.get("node_id"),
                        message_id,
                        exc,
                    )
                except FernetEncryptionException as exc:
                    db.rollback()
                    logger.exception(
                        "Fernet 암호화에 실패했습니다. node_id=%s message_id=%s error=%s",
                        fields.get("node_id"),
                        message_id,
                        exc,
                    )
                except AnalysisResultSaveException as exc:
                    db.rollback()
                    logger.exception(
                        "분석 결과 DB 저장에 실패했습니다. node_id=%s message_id=%s error=%s",
                        fields.get("node_id"),
                        message_id,
                        exc,
                    )
                except Exception:
                    db.rollback()
                    logger.exception(
                        "SLLM worker 처리 중 알 수 없는 오류가 발생했습니다. node_id=%s message_id=%s",
                        fields.get("node_id"),
                        message_id,
                    )
                finally:
                    db.close()

                last_id = message_id

                if save_succeeded:
                    logger.info(
                        "analysis_results 저장 완료 message_id=%s node_id=%s summary=%s",
                        message_id,
                        fields.get("node_id"),
                        fields.get("sllm_summary"),
                    )


if __name__ == "__main__":
    run_sllm_worker()
