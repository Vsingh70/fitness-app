from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.meal import (
    BodyMetricCreate,
    BodyMetricList,
    BodyMetricResponse,
    BodyMetricTrendPoint,
    BodyMetricTrendResponse,
    BodyMetricTrendSeries,
)
from app.services import body_metrics as svc

router = APIRouter(tags=["body-metrics"])


@router.post(
    "/body-metrics",
    response_model=BodyMetricResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_body_metric(
    payload: BodyMetricCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> BodyMetricResponse:
    record = await svc.log_metric(
        session,
        current_user,
        recorded_at=payload.recorded_at,
        weight_kg=payload.weight_kg,
        body_fat_pct=payload.body_fat_pct,
        neck_cm=payload.neck_cm,
        waist_cm=payload.waist_cm,
        hip_cm=payload.hip_cm,
    )
    await session.commit()
    return BodyMetricResponse.model_validate(record)


@router.get("/body-metrics", response_model=BodyMetricList)
async def list_body_metrics(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> BodyMetricList:
    rows = await svc.list_metrics(session, current_user, limit=limit)
    return BodyMetricList(items=[BodyMetricResponse.model_validate(r) for r in rows])


@router.get("/body-metrics/trend", response_model=BodyMetricTrendResponse)
async def body_metrics_trend(
    weeks: int = Query(default=12, ge=1, le=104),
    window: int = Query(default=4, ge=1, le=52, description="Moving-average window in weeks."),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> BodyMetricTrendResponse:
    series = await svc.trend(session, current_user, weeks=weeks, window=window)
    return BodyMetricTrendResponse(
        weeks=weeks,
        window=window,
        series=[
            BodyMetricTrendSeries(
                metric=s.metric,
                points=[
                    BodyMetricTrendPoint(
                        iso_year=p.iso_year,
                        iso_week=p.iso_week,
                        week_start=p.week_start,
                        value=p.value,
                        moving_average=p.moving_average,
                    )
                    for p in s.points
                ],
            )
            for s in series
        ],
    )


@router.delete("/body-metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_body_metric(
    metric_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_metric(session, current_user, metric_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
