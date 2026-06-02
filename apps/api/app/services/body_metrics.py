"""body_metrics CRUD + trend (weekly moving average)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.body_metric import BodyMetric
from app.models.user import User

# Metrics exposed by the trend endpoint, in display order.
TREND_METRICS: tuple[str, ...] = ("weight_kg", "body_fat_pct", "neck_cm", "waist_cm", "hip_cm")

_TWO_PLACES = Decimal("0.01")


async def log_metric(
    session: AsyncSession,
    user: User,
    *,
    recorded_at: datetime,
    weight_kg: Decimal | None = None,
    body_fat_pct: Decimal | None = None,
    neck_cm: Decimal | None = None,
    waist_cm: Decimal | None = None,
    hip_cm: Decimal | None = None,
) -> BodyMetric:
    record = BodyMetric(
        user_id=user.id,
        recorded_at=recorded_at,
        weight_kg=weight_kg,
        body_fat_pct=body_fat_pct,
        neck_cm=neck_cm,
        waist_cm=waist_cm,
        hip_cm=hip_cm,
    )
    session.add(record)
    await session.flush()
    return record


async def list_metrics(
    session: AsyncSession,
    user: User,
    *,
    limit: int = 100,
) -> list[BodyMetric]:
    stmt = (
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id)
        .order_by(desc(BodyMetric.recorded_at))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def delete_metric(session: AsyncSession, user: User, metric_id: UUID) -> None:
    record = (
        await session.execute(
            select(BodyMetric).where(BodyMetric.id == metric_id, BodyMetric.user_id == user.id)
        )
    ).scalar_one_or_none()
    if record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Body metric not found.")
    await session.delete(record)
    await session.flush()


# ---------------------------------------------------------------------------
# Trend (weekly mean + trailing moving average)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrendPoint:
    iso_year: int
    iso_week: int
    week_start: date
    value: Decimal | None
    moving_average: Decimal | None


@dataclass(frozen=True)
class TrendSeries:
    metric: str
    points: list[TrendPoint]


def _iso_monday(d: date) -> date:
    """Monday of the ISO week containing ``d``."""
    return d - timedelta(days=d.weekday())


def _mean(values: list[Decimal]) -> Decimal:
    return (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )


def _build_series(
    metric: str,
    *,
    week_buckets: list[tuple[int, int, date]],
    weekly_values: dict[date, list[Decimal]],
    window: int,
) -> TrendSeries:
    """Compute the weekly mean per bucket then a trailing moving average over
    the most recent ``window`` weeks that actually have a value (gaps skipped).
    """
    points: list[TrendPoint] = []
    history: list[Decimal] = []
    for iso_year, iso_week, monday in week_buckets:
        observed = weekly_values.get(monday)
        weekly_mean = _mean(observed) if observed else None
        if weekly_mean is not None:
            history.append(weekly_mean)
        moving_avg = _mean(history[-window:]) if history else None
        points.append(
            TrendPoint(
                iso_year=iso_year,
                iso_week=iso_week,
                week_start=monday,
                value=weekly_mean,
                moving_average=moving_avg,
            )
        )
    return TrendSeries(metric=metric, points=points)


async def trend(
    session: AsyncSession,
    user: User,
    *,
    weeks: int,
    window: int,
    today: date | None = None,
) -> list[TrendSeries]:
    """Return per-metric weekly series across the last ``weeks`` ISO weeks with
    a trailing ``window``-week moving average.

    Each metric is aggregated independently so a week is only counted for a
    metric when that metric was actually recorded that week.
    """
    anchor = today or datetime.now().date()
    current_monday = _iso_monday(anchor)
    earliest_monday = current_monday - timedelta(weeks=weeks - 1)

    # Pre-build the contiguous ordered list of week buckets (oldest -> newest).
    week_buckets: list[tuple[int, int, date]] = []
    for offset in range(weeks):
        monday = earliest_monday + timedelta(weeks=offset)
        iso_year, iso_week, _ = monday.isocalendar()
        week_buckets.append((iso_year, iso_week, monday))

    earliest_dt = datetime(earliest_monday.year, earliest_monday.month, earliest_monday.day)
    rows = list(
        (
            await session.execute(
                select(BodyMetric)
                .where(
                    BodyMetric.user_id == user.id,
                    BodyMetric.recorded_at >= earliest_dt,
                )
                .order_by(asc(BodyMetric.recorded_at))
            )
        )
        .scalars()
        .all()
    )

    # metric -> {week_monday -> [values]}
    weekly: dict[str, dict[date, list[Decimal]]] = {m: {} for m in TREND_METRICS}
    for row in rows:
        monday = _iso_monday(row.recorded_at.date())
        for metric in TREND_METRICS:
            value = getattr(row, metric)
            if value is not None:
                weekly[metric].setdefault(monday, []).append(value)

    return [
        _build_series(
            metric,
            week_buckets=week_buckets,
            weekly_values=weekly[metric],
            window=window,
        )
        for metric in TREND_METRICS
    ]
