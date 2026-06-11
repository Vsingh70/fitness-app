from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import db_session
from app.logging_config import get_logger

router = APIRouter(tags=["health"])

log = get_logger("health")


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    db: Literal["ok", "down"]


@router.get("/health", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(db_session)) -> HealthResponse:
    db_status: Literal["ok", "down"] = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        log.warning("db_health_check_failed", error=str(exc))
        db_status = "down"

    overall: Literal["ok", "degraded"] = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        version=get_settings().git_sha,
        db=db_status,
    )
