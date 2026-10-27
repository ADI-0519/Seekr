import logging
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, cast

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.error_handlers import (
    http_exception_handler,
    internal_exception_handler,
    validation_exception_handler,
)
from app.core.rate_limit import limiter
from app.db.session import close_db, init_db
from app.services.qdrant_client import QdrantService
from app.services.storage import StorageService

log = logging.getLogger(__name__)

settings = get_settings()
ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    qdrant = QdrantService()
    qdrant.ensure_collection_with_sparse()
    storage = StorageService()
    storage.ensure_bucket_exists()

    if settings.firebase_auth_enabled:
        localhost_only = all("localhost" in o or "127.0.0.1" in o for o in settings.allowed_origins)
        if localhost_only:
            log.warning(
                "Firebase auth is enabled but ALLOWED_ORIGINS only contains localhost origins. "
                "Set ALLOWED_ORIGINS to your deployed frontend URL or the frontend will be CORS-blocked."
            )

    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_exception_handler(HTTPException, cast(ExceptionHandler, http_exception_handler))
app.add_exception_handler(
    RequestValidationError, cast(ExceptionHandler, validation_exception_handler)
)
app.add_exception_handler(Exception, cast(ExceptionHandler, internal_exception_handler))

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# cors for nextjs frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_JSON_BODY_LIMIT = 64 * 1024  # 64KB


@app.middleware("http")
async def limit_json_body_size(request: Request, call_next: Callable) -> Response:
    if request.method in ("POST", "PUT", "PATCH") and "/upload" not in request.url.path:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                parsed_length = int(content_length)
            except ValueError:
                return Response(
                    content='{"status_code":400,"error":"BadRequest","detail":"Invalid Content-Length header"}',
                    status_code=400,
                    media_type="application/json",
                )

            if parsed_length < 0:
                return Response(
                    content='{"status_code":400,"error":"BadRequest","detail":"Invalid Content-Length header"}',
                    status_code=400,
                    media_type="application/json",
                )

            if parsed_length > _JSON_BODY_LIMIT:
                return Response(
                    content='{"status_code":413,"error":"PayloadTooLarge","detail":"Request body too large"}',
                    status_code=413,
                    media_type="application/json",
                )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
