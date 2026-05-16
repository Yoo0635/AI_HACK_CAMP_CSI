from typing import Any

from fastapi import status


class AppException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class WebSocketAppException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        close_code: int = 1011,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.close_code = close_code
        self.details = details
        super().__init__(message)


class DuplicateBedException(AppException):
    def __init__(self, field_name: str, field_value: str) -> None:
        super().__init__(
            message=f"이미 사용 중인 {field_name}입니다. 다른 값을 입력해주세요.",
            error_code="BED_DUPLICATE",
            status_code=status.HTTP_409_CONFLICT,
            details={
                "field": field_name,
                "value": field_value,
            },
        )


class BedCreateException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="침대 정보를 저장하지 못했습니다. 잠시 후 다시 시도해주세요.",
            error_code="BED_CREATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BedQueryException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="침대 목록을 조회하지 못했습니다. 잠시 후 다시 시도해주세요.",
            error_code="BED_QUERY_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BedNotFoundByNodeException(AppException):
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(
            message="해당 센서 노드에 연결된 침대 정보를 찾지 못했습니다.",
            error_code="BED_NOT_FOUND_BY_NODE_ID",
            status_code=status.HTTP_404_NOT_FOUND,
            details={
                "node_id": node_id,
            },
        )


class EmptyRequestBodyException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="요청 본문이 비어 있습니다. CSI 원시 패킷 바이트 데이터를 전송해주세요.",
            error_code="EMPTY_REQUEST_BODY",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class CsiLogSaveException(AppException):
    def __init__(self, node_id: str, seq_num: int) -> None:
        super().__init__(
            message="수신한 CSI 데이터를 Redis 로그에 저장하지 못했습니다.",
            error_code="CSI_LOG_SAVE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "node_id": node_id,
                "seq_num": seq_num,
            },
        )


class InvalidCsiPacketSizeException(AppException):
    def __init__(self, expected_size: int, actual_size: int) -> None:
        super().__init__(
            message=(
                "CSI 패킷 길이가 올바르지 않습니다. "
                f"{expected_size}바이트 패킷만 처리할 수 있습니다."
            ),
            error_code="CSI_PACKET_SIZE_INVALID",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "expected_size": expected_size,
                "actual_size": actual_size,
            },
        )


class CsiPacketParseException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="CSI 패킷을 해석하지 못했습니다. 패킷 구조를 다시 확인해주세요.",
            error_code="CSI_PACKET_PARSE_FAILED",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InvalidCsiPacketEncodingException(AppException):
    def __init__(self, field_name: str) -> None:
        super().__init__(
            message=f"CSI 패킷의 {field_name} 값이 UTF-8 문자열 형식이 아닙니다.",
            error_code="CSI_PACKET_ENCODING_INVALID",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "field": field_name,
            },
        )


class InvalidCsiPacketHeaderException(AppException):
    def __init__(self, actual_header: str) -> None:
        super().__init__(
            message="CSI 패킷 헤더가 올바르지 않습니다. 'CSI!' 헤더만 허용됩니다.",
            error_code="CSI_PACKET_HEADER_INVALID",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "actual_header": actual_header,
            },
        )


class InvalidCsiNodeIdException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="CSI 패킷에 node_id가 비어 있습니다. 유효한 센서 노드 ID를 포함해주세요.",
            error_code="CSI_NODE_ID_INVALID",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class WebSocketStreamReadException(WebSocketAppException):
    def __init__(self, stream_name: str) -> None:
        super().__init__(
            message="실시간 분석 스트림을 읽지 못했습니다. 연결을 다시 시도해주세요.",
            error_code="WS_STREAM_READ_FAILED",
            details={
                "stream_name": stream_name,
            },
        )


class WebSocketDatabaseException(WebSocketAppException):
    def __init__(self, action: str) -> None:
        super().__init__(
            message=f"실시간 알림 처리 중 {action} 작업에 실패했습니다.",
            error_code="WS_DATABASE_FAILED",
            details={
                "action": action,
            },
        )
