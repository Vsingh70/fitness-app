from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response

from app.config import get_settings
from app.db import dispose_engine, get_engine
from app.logging_config import configure_logging, get_logger
from app.middleware.errors import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import PrometheusMiddleware, metrics_response
from app.observability.tracing import configure_tracing
from app.routers import analytics as analytics_router
from app.routers import auth as auth_router
from app.routers import body_metrics as body_metrics_router
from app.routers import exercises as exercises_router
from app.routers import foods as foods_router
from app.routers import health as health_router
from app.routers import insights as insights_router
from app.routers import integrations_fitbit as integrations_fitbit_router
from app.routers import me as me_router
from app.routers import meal_plans as meal_plans_router
from app.routers import meals as meals_router
from app.routers import programs as programs_router
from app.routers import readiness as readiness_router
from app.routers import recommendations as recommendations_router
from app.routers import scheduling as scheduling_router
from app.routers import workouts as workouts_router


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
    app.add_middleware(PrometheusMiddleware)
    register_exception_handlers(app)
    configure_tracing(app)

    @app.get("/metrics", include_in_schema=False)
    async def metrics(request: Request) -> Response:
        return metrics_response(request, get_settings().metrics_token)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(health_router.router)
    v1.include_router(auth_router.router)
    v1.include_router(me_router.router)
    v1.include_router(exercises_router.router)
    v1.include_router(workouts_router.router)
    v1.include_router(programs_router.router)
    v1.include_router(scheduling_router.router)
    v1.include_router(recommendations_router.router)
    v1.include_router(analytics_router.router)
    v1.include_router(insights_router.router)
    v1.include_router(foods_router.router)
    v1.include_router(meals_router.router)
    v1.include_router(meal_plans_router.router)
    v1.include_router(body_metrics_router.router)
    v1.include_router(integrations_fitbit_router.router)
    v1.include_router(readiness_router.router)
    app.include_router(v1)

    return app


app = create_app()
