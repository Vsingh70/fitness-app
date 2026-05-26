import asyncio
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

    from app.config import get_settings
    from app.db import reset_engine_for_tests

    get_settings.cache_clear()
    reset_engine_for_tests(async_url)

    _run_migrations()

    yield


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

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
                "TRUNCATE TABLE exercises, refresh_tokens, users RESTART IDENTITY CASCADE"
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
