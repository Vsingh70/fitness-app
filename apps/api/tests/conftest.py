import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer


def _to_asyncpg_url(sync_url: str) -> str:
    # testcontainers returns e.g. postgresql+psycopg2://... or postgresql://...
    # Normalize to postgresql+asyncpg://.
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

    # Reset cached settings + engine so they re-read env vars.
    from app.config import get_settings
    from app.db import reset_engine_for_tests

    get_settings.cache_clear()
    reset_engine_for_tests(async_url)

    yield


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
