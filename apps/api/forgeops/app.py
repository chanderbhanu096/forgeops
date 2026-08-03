"""
FastAPI application entry point.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forgeops.api.routes import approvals, memory, metrics, missions, skills, sse
from forgeops.cache import close_redis, get_redis
from forgeops.config import get_settings
from forgeops.db import get_engine
from forgeops.logging import configure_logging
from forgeops.models import orm  # noqa: F401 — ensure models are registered

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    settings = get_settings()

    from forgeops.observability import setup_otel
    setup_otel(service_name="forgeops-api")

    log.info(
        "forgeops_starting",
        environment=settings.environment,
        primary_model=settings.primary_model,
    )

    # Warm up connections
    await get_redis()

    yield

    from forgeops.observability import get_langfuse
    get_langfuse().flush()
    await close_redis()
    await get_engine().dispose()
    log.info("forgeops_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ForgeOps AI",
        description="Autonomous AI data and cloud engineer",
        version="0.1.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "https://forgeops-staging-web.greenrock-70958585.northeurope.azurecontainerapps.io",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(missions.router, prefix="/api/v1/missions", tags=["missions"])
    app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])
    app.include_router(skills.router, prefix="/api/v1/skills", tags=["skills"])
    app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])
    app.include_router(sse.router, prefix="/api/v1/stream", tags=["stream"])
    app.include_router(metrics.router, tags=["observability"])

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
