import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer


def _to_asyncpg_url(sync_url: str) -> str:
    if sync_url.startswith("postgresql+asyncpg://"):
        return sync_url
    if sync_url.startswith("postgresql+psycopg2://"):
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise ValueError(f"Unexpected Postgres URL from testcontainers: {sync_url}")


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    container = PostgresContainer("postgres:16")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session", autouse=True)
def configure_environment(postgres_container: PostgresContainer) -> Iterator[None]:
    sync_url = postgres_container.get_connection_url()
    async_url = _to_asyncpg_url(sync_url)

    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = async_url
    os.environ["LOG_FORMAT"] = "console"
    os.environ["JWT_SECRET"] = "test-secret-please-rotate"
    os.environ["APPLE_BUNDLE_IDS"] = "com.example.gym.ios,com.example.gym.web"
    os.environ["GOOGLE_CLIENT_IDS"] = "test-google-client-id.apps.googleusercontent.com"

    import tempfile

    photo_root = tempfile.mkdtemp(prefix="meal-photos-")
    os.environ["MEAL_PHOTO_ROOT"] = photo_root
    os.environ["MEAL_PHOTO_SIGNING_SECRET"] = "test-photo-secret"

    from app.config import get_settings
    from app.db import reset_engine_for_tests

    get_settings.cache_clear()
    reset_engine_for_tests(async_url)

    _run_migrations()

    yield


def _run_migrations() -> None:
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(_alembic_ini_path()))
    cfg.set_main_option("script_location", str(_alembic_script_path()))
    command.upgrade(cfg, "head")


def _alembic_ini_path():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent / "alembic.ini"


def _alembic_script_path():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent / "alembic"


@pytest_asyncio.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    yield
    from app.db import get_sessionmaker

    sm = get_sessionmaker()
    async with sm() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE "
                "foods, "
                "muscle_volume_weekly, "
                "analytics_insights, user_fatigue_state, "
                "recommendations, "
                "sets, workout_exercises, workout_sessions, "
                "scheduled_workouts, notifications, "
                "exercise_progression, idempotency_keys, "
                "program_day_exercises, program_days, programs, program_templates, "
                "exercises, refresh_tokens, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_apple_jwks_cache() -> Iterator[None]:
    from app.services.auth import _reset_apple_jwks_cache_for_tests

    _reset_apple_jwks_cache_for_tests()
    yield


@pytest.fixture(autouse=True)
def stub_rationale_pipeline(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """By default, run the rationale generator inline (no Redis) and force
    the Ollama client to fail so the fallback path is exercised. Tests that
    want a custom Ollama response monkeypatch `app.clients.ollama.generate`
    after this fixture runs.
    """
    from uuid import UUID

    from app.clients import ollama as ollama_module
    from app.db import get_sessionmaker
    from app.services.ai import rationale_job

    async def fake_generate(**kwargs: object) -> str:
        raise ollama_module.OllamaError("ollama disabled in tests")

    monkeypatch.setattr(ollama_module, "generate", fake_generate)

    async def inline_enqueue(rec_id: UUID) -> None:
        sm = get_sessionmaker()
        async with sm() as session:
            await rationale_job.rationalize_recommendation_inline(session, rec_id)
            await session.commit()

    monkeypatch.setattr(rationale_job, "enqueue_for_recommendation", inline_enqueue)
    yield


@pytest.fixture(autouse=True)
def stub_rate_limit_redis(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Replace the rate-limit Redis client with an in-memory counter so the
    test suite doesn't require a running Redis. Tests that want to exercise
    the limit can monkeypatch this further.
    """
    from app.services import rate_limit

    counters: dict[str, int] = {}

    class _Fake:
        async def incr(self, key: str) -> int:
            counters[key] = counters.get(key, 0) + 1
            return counters[key]

        async def expire(self, key: str, seconds: int) -> bool:
            return True

        async def close(self) -> None:
            return None

    async def fake_get_redis() -> _Fake:
        return _Fake()

    monkeypatch.setattr(rate_limit, "_get_redis", fake_get_redis)
    rate_limit.reset_concurrency_for_tests()
    yield


@pytest.fixture(autouse=True)
def stub_rollup_pipeline(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Run analytics rollups inline so the table is populated synchronously
    in tests. Avoids the Redis dependency for routes that enqueue rollups.
    """
    from uuid import UUID

    from app.db import get_sessionmaker
    from app.services.analytics import enqueue as enqueue_module
    from app.services.analytics import volume as volume_service

    async def inline_rollup(user_id: UUID, iso_year: int, iso_week: int) -> None:
        sm = get_sessionmaker()
        async with sm() as session:
            await volume_service.rollup_user_week(session, user_id, iso_year, iso_week)
            await session.commit()

    monkeypatch.setattr(enqueue_module, "enqueue_rollup", inline_rollup)
    yield
