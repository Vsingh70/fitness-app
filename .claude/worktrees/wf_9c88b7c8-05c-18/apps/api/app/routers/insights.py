from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.analytics_insight import AnalyticsInsight
from app.models.enums import AnalyticsInsightKind, AnalyticsInsightSeverity
from app.models.user import User
from app.schemas.analytics import (
    InsightList,
    InsightResponse,
    RecomputeInsightsResponse,
)
from app.services.analytics import insights as svc
from app.services.pagination import (
    decode_created_at_id_cursor,
    encode_created_at_id_cursor,
)

router = APIRouter(tags=["insights"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@router.get("/insights", response_model=InsightList)
async def list_insights(
    kind: AnalyticsInsightKind | None = Query(default=None),
    severity: AnalyticsInsightSeverity | None = Query(default=None),
    dismissed: bool = Query(default=False),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> InsightList:
    stmt = (
        select(AnalyticsInsight)
        .where(AnalyticsInsight.user_id == current_user.id)
        .order_by(AnalyticsInsight.created_at.desc(), AnalyticsInsight.id.desc())
        .limit(limit + 1)
    )
    if kind is not None:
        stmt = stmt.where(AnalyticsInsight.kind == kind)
    if severity is not None:
        stmt = stmt.where(AnalyticsInsight.severity == severity)
    if dismissed:
        stmt = stmt.where(AnalyticsInsight.dismissed_at.is_not(None))
    else:
        stmt = stmt.where(AnalyticsInsight.dismissed_at.is_(None))

    decoded = decode_created_at_id_cursor(cursor)
    if decoded is not None:
        cursor_created, cursor_id = decoded
        stmt = stmt.where(
            or_(
                AnalyticsInsight.created_at < cursor_created,
                and_(
                    AnalyticsInsight.created_at == cursor_created,
                    AnalyticsInsight.id < cursor_id,
                ),
            )
        )

    rows = list((await session.execute(stmt)).scalars().all())
    next_cursor: str | None = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_created_at_id_cursor(last.created_at, last.id)
    return InsightList(
        items=[InsightResponse.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.post("/insights/recompute", response_model=RecomputeInsightsResponse)
async def recompute_insights(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RecomputeInsightsResponse:
    ids = await svc.compute_insights_for_user(session, current_user)
    await session.commit()
    return RecomputeInsightsResponse(count=len(ids))


@router.post("/insights/{insight_id}/dismiss", response_model=InsightResponse)
async def dismiss_insight(
    insight_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> InsightResponse:
    record = (
        await session.execute(
            select(AnalyticsInsight).where(
                AnalyticsInsight.id == insight_id,
                AnalyticsInsight.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Insight not found.")
    if record.dismissed_at is None:
        record.dismissed_at = datetime.now(tz=UTC)
        await session.commit()
    return InsightResponse.model_validate(record)
