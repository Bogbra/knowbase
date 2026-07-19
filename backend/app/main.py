import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import sqlalchemy as sa
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.core.limiter import limiter
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIDMiddleware,
    RequestTimingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import close_pool, get_client
from app.db.seed import run_seed
from app.db.session import AsyncSessionLocal

configure_logging("DEBUG" if settings.DEBUG else "INFO")
logger = logging.getLogger(__name__)

# Reject bodies larger than the configured upload limit plus JSON/multipart overhead.
# This check happens before the body is parsed into memory, preventing OOM on oversized requests.
_MAX_BODY_BYTES = settings.MAX_UPLOAD_SIZE_BYTES + 1024 * 64


class _BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            body = (
                '{"type":"https://knowbase.dev/errors/payload-too-large",'
                '"title":"Payload Too Large","status":413}'
            )
            return StarletteResponse(
                content=body,
                status_code=413,
                media_type="application/problem+json",
            )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup", extra={"env": settings.ENVIRONMENT})
    if not settings.is_production:
        # Seed is dev/demo data only. Never run in production — it would create
        # a well-known admin account (admin@knowbase.dev / Admin1234!) on every
        # fresh deployment.
        try:
            await run_seed()
        except Exception:
            logger.warning("seed_skipped", exc_info=True)
    yield
    await close_pool()
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

    app.add_middleware(_BodySizeLimitMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    from app.api.v1 import router as v1_router

    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["ops"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": settings.APP_VERSION})

    @app.get("/ready", tags=["ops"])
    async def ready() -> JSONResponse:
        result: dict[str, str] = {"status": "ready"}
        status_code = 200

        try:
            async with AsyncSessionLocal() as session:
                await session.execute(sa.text("SELECT 1"))
            result["db"] = "ok"
        except Exception:
            result["db"] = "error"
            result["status"] = "error"
            status_code = 503

        try:
            redis = get_client()
            await redis.ping()
            await redis.aclose()
            result["redis"] = "ok"
        except Exception:
            result["redis"] = "error"
            result["status"] = "error"
            status_code = 503

        return JSONResponse(result, status_code=status_code)

    @app.get("/metrics", tags=["ops"])
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
