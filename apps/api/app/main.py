from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import APIRouter, FastAPI

from app.config import get_settings
from app.db import dispose_engine, get_engine
from app.logging_config import configure_logging, get_logger
from app.middleware.errors import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import health as health_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("startup")
    settings = get_settings()
    get_engine()
    log.info("api_starting", environment=settings.environment, version=settings.git_sha)
    try:
        yield
    finally:
        await dispose_engine()
        log.info("api_stopped")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Gym API",
        version=get_settings().git_sha,
        lifespan=lifespan,
    )

    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(health_router.router)
    app.include_router(v1)

    return app


app = create_app()
