from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode:
    BAD_REQUEST = "bad_request"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    INTERNAL_ERROR = "internal_error"
    HTTP_ERROR = "http_error"


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def code_for_http_status(status_code: int) -> str:
    return {
        400: ErrorCode.BAD_REQUEST,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        422: ErrorCode.VALIDATION_ERROR,
    }.get(status_code, ErrorCode.HTTP_ERROR)


async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "request failed"
    return error_response(exc.status_code, code_for_http_status(exc.status_code), message)


async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"location": list(item.get("loc", ())), "message": item.get("msg", "invalid value")}
        for item in exc.errors()
    ]
    message = errors[0]["message"] if errors else "invalid request"
    return error_response(422, ErrorCode.VALIDATION_ERROR, message, errors)
