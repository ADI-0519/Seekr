import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.log_safety import safe_exception_message

log = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error": exc.__class__.__name__,
            "detail": exc.detail,
        },
    )


async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error(
        "Unhandled exception on %s %s: %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        safe_exception_message(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "error": "InternalServerError",
            "detail": "An unexpected error occurred.",
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "field": " -> ".join(str(loc_part) for loc_part in e["loc"]),
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "status_code": 422,
            "error": "ValidationError",
            "detail": errors,
        },
    )
