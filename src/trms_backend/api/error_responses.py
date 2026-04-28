from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


LOGGER = logging.getLogger("trms_backend.api")
REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ERROR_CODE_BY_STATUS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
    status.HTTP_413_CONTENT_TOO_LARGE: "content_too_large",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
}

_MESSAGE_BY_STATUS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "request could not be processed",
    status.HTTP_401_UNAUTHORIZED: "authentication is required or has expired",
    status.HTTP_403_FORBIDDEN: "actor is not allowed to perform this action",
    status.HTTP_404_NOT_FOUND: "requested resource was not found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "request method is not allowed for this resource",
    status.HTTP_409_CONFLICT: "request conflicts with current resource state",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal server error",
    status.HTTP_413_CONTENT_TOO_LARGE: "request payload is too large",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "request content type is not supported",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "request validation failed",
}


def build_request_id() -> str:
    return f"req_{uuid4().hex}"


def normalize_request_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if _REQUEST_ID_PATTERN.fullmatch(normalized) is None:
        return None
    return normalized


def ensure_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    if request_id is None:
        request_id = build_request_id()
    request.state.request_id = request_id
    return request_id


def build_error_payload(
    *,
    status_code: int,
    request_id: str,
    detail: Any | None = None,
    code: str | None = None,
    message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code or _ERROR_CODE_BY_STATUS.get(status_code, "http_error"),
        "message": message or _MESSAGE_BY_STATUS.get(status_code, "request failed"),
        "request_id": request_id,
    }
    if detail is not None:
        payload["detail"] = detail
    if extra:
        payload.update(extra)
    return payload


def build_error_response(
    *,
    status_code: int,
    request_id: str,
    detail: Any | None = None,
    code: str | None = None,
    message: str | None = None,
    headers: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    response_headers = dict(headers or {})
    response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code,
        headers=response_headers,
        content=jsonable_encoder(
            build_error_payload(
                status_code=status_code,
                request_id=request_id,
                detail=detail,
                code=code,
                message=message,
                extra=extra,
            )
        ),
    )


def register_error_response_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, error: StarletteHTTPException):
        return build_error_response(
            status_code=error.status_code,
            request_id=ensure_request_id(request),
            detail=error.detail,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, error: RequestValidationError):
        return build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            request_id=ensure_request_id(request),
            detail=error.errors(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, error: Exception):
        request_id = ensure_request_id(request)
        LOGGER.exception(
            "unhandled request error method=%s route=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
            extra={"request_id": request_id},
        )
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            detail="internal server error",
        )
