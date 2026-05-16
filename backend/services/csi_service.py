import json
import struct

from redis.exceptions import RedisError

from backend.config.redis import redis_client
from backend.config.redis_streams import CSI_LOG_NAME
from backend.exceptions.custom_exception import (
    CsiPacketParseException,
    CsiLogSaveException,
    EmptyRequestBodyException,
    InvalidCsiNodeIdException,
    InvalidCsiPacketEncodingException,
    InvalidCsiPacketHeaderException,
    InvalidCsiPacketSizeException,
)
from backend.schemas.response.csi_response import CsiRawResponse


PACKET_SIZE = 280
PACKET_FORMAT = "<4s8sIIi64f"


def process_csi_raw_data(body: bytes) -> CsiRawResponse:
    if not body:
        raise EmptyRequestBodyException()

    _, node_id, detected_at, seq_num, rssi, csi_data = parse_csi_packet(body)

    save_csi_log_to_redis(
        node_id=node_id,
        seq_num=seq_num,
        csi_data=csi_data,
        rssi=rssi,
        detected_at=detected_at,
    )

    return CsiRawResponse(
        message="CSI 데이터 수신이 완료되었습니다.",
        node_id=node_id,
        seq_num=seq_num,
    )


def parse_csi_packet(body: bytes) -> tuple[str, str, int, int, int, list[float]]:
    if len(body) != PACKET_SIZE:
        raise InvalidCsiPacketSizeException(
            expected_size=PACKET_SIZE,
            actual_size=len(body),
        )

    try:
        header_tag_bytes, node_id_bytes, detected_at, seq_num, rssi, *csi_data = struct.unpack(
            PACKET_FORMAT,
            body,
        )
    except struct.error as exc:
        raise CsiPacketParseException() from exc

    try:
        header_tag = header_tag_bytes.decode("utf-8").strip("\x00")
    except UnicodeDecodeError as exc:
        raise InvalidCsiPacketEncodingException("header_tag") from exc

    try:
        node_id = node_id_bytes.decode("utf-8").strip("\x00")
    except UnicodeDecodeError as exc:
        raise InvalidCsiPacketEncodingException("node_id") from exc

    if header_tag != "CSI!":
        raise InvalidCsiPacketHeaderException(header_tag)

    if not node_id:
        raise InvalidCsiNodeIdException()

    return header_tag, node_id, detected_at, seq_num, rssi, list(csi_data)


def save_csi_log_to_redis(
    node_id: str,
    seq_num: int,
    csi_data: list[float],
    rssi: int,
    detected_at: int,
) -> None:
    try:
        redis_client.xadd(
            CSI_LOG_NAME,
            {
                "node_id": node_id,
                "seq_num": seq_num,
                "csi_matrix": json.dumps(csi_data),
                "rssi": rssi,
                "detected_at": detected_at,
            },
            maxlen=200,
            approximate=True,
        )
    except RedisError as exc:
        raise CsiLogSaveException(node_id=node_id, seq_num=seq_num) from exc
