from typing import Any

from arq.connections import RedisSettings

from app.config import get_settings
from app.logging_config import configure_logging, get_logger


async def healthcheck(_ctx: dict[str, Any]) -> str:
    log = get_logger("worker")
    log.info("worker_healthcheck")
    return "ok"


async def startup(_ctx: dict[str, Any]) -> None:
    configure_logging()
    log = get_logger("worker")
    log.info("worker_started")


async def shutdown(_ctx: dict[str, Any]) -> None:
    get_logger("worker").info("worker_stopped")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    functions = [healthcheck]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
