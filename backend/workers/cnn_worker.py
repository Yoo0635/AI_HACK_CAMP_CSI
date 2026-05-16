import json
import logging

from redis.exceptions import RedisError

from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_LOG_NAME
from backend.services.analysis_result_service import (
    AnalysisResultRedisSaveException,
    save_analysis_result_redis,
)
from backend.workers.cnn_analysis_model import analyze_csi_with_cnn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_cnn_worker() -> None:
    last_id = "0-0"

    while True:
        try:
            stream_data = redis_client.xread(
                {
                    CSI_LOG_NAME: last_id,
                },
                count=1,
                block=1000,
            )
        except RedisError:
            logger.exception(
                "CSI 로그 Stream 조회에 실패했습니다. stream=%s last_id=%s",
                CSI_LOG_NAME,
                last_id,
            )
            continue

        if not stream_data:
            continue

        _, messages = stream_data[0]

        for message_id, fields in messages:
            try:
                node_id = str(fields["node_id"])
                seq_num = int(fields["seq_num"])
                csi_matrix = json.loads(fields["csi_matrix"])
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                logger.exception(
                    "CNN worker 입력 데이터 파싱에 실패했습니다. message_id=%s fields=%s",
                    message_id,
                    fields,
                )
                last_id = message_id
                continue

            try:
                cnn_result = analyze_csi_with_cnn(csi_matrix)
            except Exception:
                logger.exception(
                    "CNN 모델 분석에 실패했습니다. node_id=%s seq_num=%s message_id=%s",
                    node_id,
                    seq_num,
                    message_id,
                )
                last_id = message_id
                continue

            logger.info(
                "CNN 분석 결과 node_id=%s seq_num=%s label=%s cnn_score=%s energy=%s risk_score=%s is_anomaly=%s cnn_timestamp=%s",
                node_id,
                seq_num,
                cnn_result.get("label"),
                cnn_result.get("cnn_score"),
                cnn_result.get("energy"),
                cnn_result.get("risk_score"),
                cnn_result.get("is_anomaly"),
                cnn_result.get("cnn_timestamp"),
            )

            analysis_fields = {
                "node_id": node_id,
                "seq_num": seq_num,
                **cnn_result,
            }

            try:
                analysis_message_id = save_analysis_result_redis(analysis_fields)
            except AnalysisResultRedisSaveException:
                logger.exception(
                    "CNN 분석 결과를 analysis stream에 저장하지 못했습니다. node_id=%s seq_num=%s",
                    node_id,
                    seq_num,
                )
                last_id = message_id
                continue
            except Exception:
                logger.exception(
                    "CNN worker가 analysis stream 저장 중 알 수 없는 오류를 만났습니다. node_id=%s seq_num=%s",
                    node_id,
                    seq_num,
                )
                last_id = message_id
                continue

            logger.info(
                "CNN worker 처리 완료 csi_message_id=%s analysis_message_id=%s node_id=%s seq_num=%s",
                message_id,
                analysis_message_id,
                node_id,
                seq_num,
            )

            last_id = message_id


if __name__ == "__main__":
    run_cnn_worker()
