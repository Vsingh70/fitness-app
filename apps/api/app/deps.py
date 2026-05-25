from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


async def db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session
