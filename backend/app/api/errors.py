from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from slowapi.errors import RateLimitExceeded

from app.api.schema import ErrorDetail, ErrorEnvelope

logger = structlog.get_logger(__name__)


def error_envelope(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return ErrorEnvelope(error=ErrorDetail(code=code, message=message, details=details)).model_dump()


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    structlog.contextvars.bind_contextvars(path=str(request.url.path), status_code=exc.status_code)
    logger.warning("http_exception", detail=exc.detail)
    body = error_envelope(
        code=f"http_{exc.status_code}",
        message=str(exc.detail) if exc.detail else exc.status_code,
        details=None,
    )
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(body))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("validation_error", errors=exc.errors())
    body = error_envelope(
        code="validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )
    return JSONResponse(status_code=422, content=jsonable_encoder(body))


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    detail = getattr(exc, "detail", str(exc))
    logger.warning("rate_limit_exceeded", detail=str(detail))
    body = error_envelope(code="rate_limit_exceeded", message=str(detail), details=None)
    return JSONResponse(status_code=429, content=jsonable_encoder(body))


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=exc)
    body = error_envelope(
        code="internal_error",
        message="An unexpected error occurred",
        details=None,
    )
    return JSONResponse(status_code=500, content=jsonable_encoder(body))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
