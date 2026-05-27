"""Daily readiness score from sleep + RHR + HRV.

Formula (per spec):

    sleep_component  = clip(sleep_minutes / 480, 0, 1) * 40
    rhr_component    = clip(1 - (rhr - baseline_rhr) / 10, 0, 1) * 30
    hrv_component    = clip(hrv_ms / baseline_hrv_ms, 0, 1) * 30
    readiness_score  = round(sleep + rhr + hrv)

When HRV is missing (no value today, or no baseline available), redistribute
the 30 points evenly: sleep weight becomes 55 and rhr weight becomes 45.

Baselines are 14-day medians strictly BEFORE the target date so today's value
doesn't pull its own baseline.

Bands:
- 0..40   low      (recommend a deload-style session or rest)
- 41..70  moderate (default targets, cap top RPE at 8)
- 71..100 high     (proceed as planned, can push)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_metric import DailyMetric

BaselineWindow = 14
SLEEP_TARGET_MINUTES = 480
RHR_TOLERANCE_BPM = 10

Band = Literal["low", "moderate", "high"]


@dataclass(frozen=True)
class ReadinessBreakdown:
    sleep_component: Decimal
    rhr_component: Decimal
    hrv_component: Decimal
    score: int
    band: Band
    hrv_used: bool


def _clip(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _median(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return ((ordered[mid - 1] + ordered[mid]) / Decimal("2")).quantize(Decimal("0.01"))


def severity_band(score: int) -> Band:
    if score <= 40:
        return "low"
    if score <= 70:
        return "moderate"
    return "high"


def compute_readiness_score(
    *,
    sleep_minutes: int | None,
    rhr: int | None,
    hrv_ms: Decimal | None,
    baseline_rhr: Decimal | None,
    baseline_hrv_ms: Decimal | None,
) -> ReadinessBreakdown:
    """Pure formula. Returns the per-component breakdown + integer score + band.

    If sleep/rhr inputs are missing, that component contributes 0 (the user
    just didn't sleep well or didn't wear the watch). If HRV is missing OR
    its baseline is missing, the 30 HRV points are redistributed evenly to
    sleep (+15) and rhr (+15).
    """
    hrv_usable = hrv_ms is not None and baseline_hrv_ms not in (None, Decimal("0"))
    sleep_weight = Decimal("40") if hrv_usable else Decimal("55")
    rhr_weight = Decimal("30") if hrv_usable else Decimal("45")
    hrv_weight = Decimal("30") if hrv_usable else Decimal("0")

    if sleep_minutes is None or sleep_minutes <= 0:
        sleep_component = Decimal("0")
    else:
        ratio = Decimal(sleep_minutes) / Decimal(SLEEP_TARGET_MINUTES)
        sleep_component = (_clip(ratio, Decimal("0"), Decimal("1")) * sleep_weight).quantize(
            Decimal("0.01")
        )

    if rhr is None or baseline_rhr is None or baseline_rhr <= 0:
        rhr_component = Decimal("0")
    else:
        delta = Decimal(rhr) - baseline_rhr
        improvement = Decimal("1") - (delta / Decimal(RHR_TOLERANCE_BPM))
        rhr_component = (_clip(improvement, Decimal("0"), Decimal("1")) * rhr_weight).quantize(
            Decimal("0.01")
        )

    if not hrv_usable or hrv_ms is None or baseline_hrv_ms is None or baseline_hrv_ms == 0:
        hrv_component = Decimal("0")
    else:
        ratio = hrv_ms / baseline_hrv_ms
        hrv_component = (_clip(ratio, Decimal("0"), Decimal("1")) * hrv_weight).quantize(
            Decimal("0.01")
        )

    raw_score = sleep_component + rhr_component + hrv_component
    score = int(raw_score.to_integral_value(rounding="ROUND_HALF_UP"))
    score = max(0, min(100, score))
    return ReadinessBreakdown(
        sleep_component=sleep_component,
        rhr_component=rhr_component,
        hrv_component=hrv_component,
        score=score,
        band=severity_band(score),
        hrv_used=hrv_usable,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


async def _baselines(
    session: AsyncSession, user_id: UUID, *, target_date: date
) -> tuple[Decimal | None, Decimal | None]:
    since = target_date - timedelta(days=BaselineWindow)
    rows = (
        await session.execute(
            select(DailyMetric.resting_hr, DailyMetric.hrv_ms).where(
                DailyMetric.user_id == user_id,
                DailyMetric.date >= since,
                DailyMetric.date < target_date,
            )
        )
    ).all()
    rhr_values = [Decimal(r) for r, _ in rows if r is not None]
    hrv_values = [Decimal(h) for _, h in rows if h is not None]
    return _median(rhr_values), _median(hrv_values)


async def _today_metric(
    session: AsyncSession, user_id: UUID, *, target_date: date
) -> DailyMetric | None:
    return (
        await session.execute(
            select(DailyMetric).where(
                DailyMetric.user_id == user_id, DailyMetric.date == target_date
            )
        )
    ).scalar_one_or_none()


async def recompute_for_user_date(
    session: AsyncSession, user_id: UUID, *, target_date: date
) -> ReadinessBreakdown | None:
    """Compute readiness for a single user-day. Upserts into daily_metrics.

    Returns None when the day has no sleep/RHR/HRV data at all (so we don't
    write a synthetic 0 score for days the user didn't wear the watch).

    Side effect: when the band transitions from non-low to low, bump the
    user's rolling 7-day fatigue score by +1 (per the 04.03 accumulator).
    Idempotent across re-runs because the transition check uses the
    previously stored score.
    """
    today = await _today_metric(session, user_id, target_date=target_date)
    if today is None or (
        today.sleep_minutes is None and today.resting_hr is None and today.hrv_ms is None
    ):
        return None
    baseline_rhr, baseline_hrv = await _baselines(session, user_id, target_date=target_date)
    breakdown = compute_readiness_score(
        sleep_minutes=today.sleep_minutes,
        rhr=today.resting_hr,
        hrv_ms=today.hrv_ms,
        baseline_rhr=baseline_rhr,
        baseline_hrv_ms=baseline_hrv,
    )
    previous_score = today.readiness_score
    stmt = (
        pg_insert(DailyMetric)
        .values(
            user_id=user_id,
            date=target_date,
            readiness_score=breakdown.score,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "date"],
            set_={"readiness_score": breakdown.score, "updated_at": datetime.now(tz=UTC)},
        )
    )
    await session.execute(stmt)
    await session.flush()

    previously_low = previous_score is not None and severity_band(previous_score) == "low"
    if breakdown.band == "low" and not previously_low:
        await _bump_fatigue_for_low_readiness(session, user_id)

    return breakdown


async def _bump_fatigue_for_low_readiness(session: AsyncSession, user_id: UUID) -> None:
    """Add +1 to the user's rolling 7d fatigue score per 04.03 spec."""
    from app.models.user_fatigue_state import UserFatigueState
    from app.services.progression.mesocycle import FATIGUE_LOW_READINESS

    state = (
        await session.execute(select(UserFatigueState).where(UserFatigueState.user_id == user_id))
    ).scalar_one_or_none()
    now = datetime.now(tz=UTC)
    if state is None:
        state = UserFatigueState(
            user_id=user_id,
            rolling_7d_score=FATIGUE_LOW_READINESS,
            last_event_at=now,
        )
        session.add(state)
    else:
        state.rolling_7d_score = state.rolling_7d_score + FATIGUE_LOW_READINESS
        state.last_event_at = now
    await session.flush()


async def recompute_recent_for_user(
    session: AsyncSession, user_id: UUID, *, today: date | None = None
) -> list[tuple[date, ReadinessBreakdown]]:
    """Recompute the last 14 days. Returns the (date, breakdown) tuples that
    were written.
    """
    today = today or datetime.now(tz=UTC).date()
    out: list[tuple[date, ReadinessBreakdown]] = []
    for offset in range(BaselineWindow):
        target = today - timedelta(days=offset)
        breakdown = await recompute_for_user_date(session, user_id, target_date=target)
        if breakdown is not None:
            out.append((target, breakdown))
    return out


async def get_today(
    session: AsyncSession, user_id: UUID, *, today: date | None = None
) -> DailyMetric | None:
    today = today or datetime.now(tz=UTC).date()
    return await _today_metric(session, user_id, target_date=today)


async def history(
    session: AsyncSession, user_id: UUID, *, from_date: date, to_date: date
) -> list[DailyMetric]:
    rows = (
        (
            await session.execute(
                select(DailyMetric)
                .where(
                    DailyMetric.user_id == user_id,
                    DailyMetric.date >= from_date,
                    DailyMetric.date <= to_date,
                )
                .order_by(DailyMetric.date.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)
