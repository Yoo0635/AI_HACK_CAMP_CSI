import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.exceptions.custom_exception import AppException

logger = logging.getLogger(__name__)


def _format_validation_field(loc: tuple) -> str:
    if not loc:
        return "request"

    parts = [str(part) for part in loc if part not in {"body"}]
    return ".".join(parts) if parts else "request"


def _translate_validation_message(error: dict) -> str:
    error_type = error.get("type", "")
    error_msg = error.get("msg", "")
    ctx = error.get("ctx", {})

    message_map = {
        "missing": "필수 항목입니다.",
        "string_type": "문자열 형식이어야 합니다.",
        "int_parsing": "정수를 입력해야 합니다.",
        "int_type": "정수 형식이어야 합니다.",
        "float_parsing": "숫자를 입력해야 합니다.",
        "float_type": "숫자 형식이어야 합니다.",
        "bool_parsing": "참 또는 거짓 값을 입력해야 합니다.",
        "bool_type": "불리언 형식이어야 합니다.",
        "list_type": "배열 형식이어야 합니다.",
        "dict_type": "객체 형식이어야 합니다.",
        "literal_error": "허용되지 않은 값입니다.",
        "json_invalid": "JSON 형식이 올바르지 않습니다.",
    }

    if error_type == "value_error" and error_msg.startswith("Value error, "):
        return error_msg.removeprefix("Value error, ")

    if error_type == "string_too_short":
        return f"최소 {ctx.get('min_length')}자 이상 입력해야 합니다."

    if error_type == "string_too_long":
        return f"최대 {ctx.get('max_length')}자까지만 입력할 수 있습니다."

    if error_type == "greater_than_equal":
        return f"{ctx.get('ge')} 이상이어야 합니다."

    if error_type == "less_than_equal":
        return f"{ctx.get('le')} 이하여야 합니다."

    return message_map.get(error_type, "요청 형식이 올바르지 않습니다.")


def _build_error_payload(
    request: Request,
    message: str,
    error_code: str,
    *,
    details: dict | None = None,
    errors: list[dict] | None = None,
) -> dict:
    payload = {
        "message": message,
        "error_code": error_code,
        "path": request.url.path,
    }

    if details:
        payload["details"] = details

    if errors:
        payload["errors"] = errors

    return payload


def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    logger.warning(
        "애플리케이션 예외가 발생했습니다. path=%s error_code=%s message=%s",
        request.url.path,
        exc.error_code,
        exc.message,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(
            request,
            exc.message,
            exc.error_code,
            details=exc.details,
        ),
    )


def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": _format_validation_field(error.get("loc", ())),
            "message": _translate_validation_message(error),
            "rejected_value": error.get("input"),
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_build_error_payload(
            request,
            "요청값 검증에 실패했습니다. 입력 항목을 다시 확인해주세요.",
            "INVALID_REQUEST",
            errors=errors,
        ),
    )


def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    status_code_map = {
        status.HTTP_404_NOT_FOUND: (
            "요청한 경로를 찾지 못했습니다.",
            "NOT_FOUND",
        ),
        status.HTTP_405_METHOD_NOT_ALLOWED: (
            "허용되지 않은 HTTP 메서드입니다.",
            "METHOD_NOT_ALLOWED",
        ),
    }

    message, error_code = status_code_map.get(
        exc.status_code,
        (
            exc.detail if isinstance(exc.detail, str) else "요청을 처리하지 못했습니다.",
            "HTTP_ERROR",
        ),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(request, message, error_code),
    )


def response_validation_exception_handler(
    request: Request,
    exc: ResponseValidationError,
) -> JSONResponse:
    logger.exception(
        "응답 검증에 실패했습니다. path=%s",
        request.url.path,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_payload(
            request,
            "서버 응답 생성 중 오류가 발생했습니다.",
            "RESPONSE_VALIDATION_ERROR",
        ),
    )


def internal_server_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("처리되지 않은 예외가 발생했습니다.", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_payload(
            request,
            "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "INTERNAL_SERVER_ERROR",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        AppException,
        app_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(
        ResponseValidationError,
        response_validation_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        internal_server_exception_handler,
    )
