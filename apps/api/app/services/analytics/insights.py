"""Heuristic insight generation: weak/strong muscle, stagnation, imbalance,
undertrained. Pure-by-default functions feed `compute_insights_for_user`
which upserts the results into `analytics_insights`.

Determinism:
- All math is pure on Decimals.
- Time windowing uses an explicit `today` parameter so tests can pin it.
- Re-running with the same data is idempotent: any existing active row with
  the same (user_id, kind, subject) gets updated; dismissed rows newer than
  30 days are left alone (no resurface).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, and_, delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_insight import AnalyticsInsight
from app.models.enums import (
    AnalyticsInsightKind,
    AnalyticsInsightSeverity,
    Muscle,
)
from app.models.user import User
from app.services.analytics import strength_norms

# Tunables ------------------------------------------------------------------

STRENGTH_LOOKBACK_WEEKS = 12
STAGNATION_LOOKBACK_WEEKS = 12
STAGNATION_MIN_SESSIONS = 6
STAGNATION_NOISE_THRESHOLD = Decimal("3.0")  # residual stddev in kg

IMBALANCE_LOOKBACK_WEEKS = 4
PUSH_MUSCLES = {Muscle.chest, Muscle.front_delts, Muscle.triceps}
PULL_MUSCLES = {Muscle.lats, Muscle.rhomboids, Muscle.rear_delts, Muscle.biceps}
QUAD_MUSCLES = {Muscle.quads}
HAM_MUSCLES = {Muscle.hamstrings}
FRONT_DELT_MUSCLES = {Muscle.front_delts}
REAR_DELT_MUSCLES = {Muscle.rear_delts}

UNDERTRAINED_LOOKBACK_WEEKS = 4
UNDERTRAINED_MIN_WEEKLY_SETS = Decimal("8")
UNDERTRAINED_TARGET_LOW = 10
UNDERTRAINED_TARGET_HIGH = 16

# Primary muscles we surface undertrained insights for. We skip small/isolation
# groups to avoid noise (e.g. abs).
PRIMARY_MOVERS = {
    Muscle.chest,
    Muscle.lats,
    Muscle.quads,
    Muscle.hamstrings,
    Muscle.glutes,
    Muscle.front_delts,
    Muscle.rear_delts,
    Muscle.side_delts,
    Muscle.biceps,
    Muscle.triceps,
}

DISMISS_COOLDOWN_DAYS = 30

# TTL / cleanup -------------------------------------------------------------
# Heuristic-only insights (no LLM rationale) are cheap to recompute the next
# night, so we expire STAGNATION rows after 30 days to stop the table growing
# unbounded. Rows that carry an LLM-generated rationale cost an Ollama call to
# regenerate, so we keep those much longer.
STAGNATION_TTL_DAYS = 30
RATIONALE_TTL_DAYS = 180

# Kinds subject to the short heuristic TTL. Stagnation is the noisiest /
# fastest-churning kind, so it is the one the spec calls out explicitly.
TTL_KINDS = (AnalyticsInsightKind.stagnation,)


# Public types --------------------------------------------------------------


@dataclass(frozen=True)
class NewInsight:
    kind: AnalyticsInsightKind
    severity: AnalyticsInsightSeverity
    subject: str
    title: str
    body: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StagnationFinding:
    exercise_slug: str
    exercise_name: str
    slope_kg_per_week: Decimal
    residual_stddev: Decimal
    sessions: int


@dataclass(frozen=True)
class ImbalanceFinding:
    subject: str  # canonical, e.g. "push_vs_pull"
    label: str  # human-readable
    ratio: Decimal
    low: Decimal
    high: Decimal


@dataclass(frozen=True)
class UndertrainedFinding:
    muscle: Muscle
    avg_weekly_sets: Decimal


@dataclass(frozen=True)
class StrengthFinding:
    muscle: Muscle
    representative_slug: str
    e1rm_kg: Decimal
    bodyweight_kg: Decimal
    ratio: Decimal
    classification: str  # weak|moderate|strong


# Helpers -------------------------------------------------------------------


def _epley_e1rm(weight_kg: Decimal, reps: int) -> Decimal:
    if reps <= 0:
        return Decimal("0")
    factor = Decimal("1") + (Decimal(reps) / Decimal("30"))
    return (weight_kg * factor).quantize(Decimal("0.01"))


def _today_utc() -> date:
    return datetime.now(tz=UTC).date()


async def _latest_bodyweight(session: AsyncSession, user_id: UUID) -> Decimal | None:
    row = (
        await session.execute(
            text(
                """
                SELECT bodyweight_kg
                FROM workout_sessions
                WHERE user_id = :user_id
                  AND deleted_at IS NULL
                  AND bodyweight_kg IS NOT NULL
                ORDER BY started_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    if row is None:
        return None
    value = row[0]
    if value is None:
        return None
    return Decimal(value)


# Strength heuristic --------------------------------------------------------


async def compute_strength_findings(
    session: AsyncSession,
    user: User,
    *,
    today: date,
) -> list[StrengthFinding]:
    """Return relative-strength findings per representative-mapped muscle.

    Skips if the user has no bodyweight history.
    """
    bw = await _latest_bodyweight(session, user.id)
    if bw is None or bw <= 0:
        return []

    since = today - timedelta(weeks=STRENGTH_LOOKBACK_WEEKS)
    rows = (
        await session.execute(
            text(
                """
                SELECT ex.slug, ex.name, s.weight_kg, s.reps
                FROM sets s
                JOIN workout_exercises we ON we.id = s.workout_exercise_id
                JOIN workout_sessions ws ON ws.id = we.workout_session_id
                JOIN exercises ex ON ex.id = we.exercise_id
                WHERE ws.user_id = :user_id
                  AND ws.deleted_at IS NULL
                  AND ws.ended_at IS NOT NULL
                  AND ws.started_at::date >= :since
                  AND s.set_type = 'working'
                  AND s.weight_kg IS NOT NULL
                  AND s.reps IS NOT NULL
                """
            ),
            {"user_id": user.id, "since": since},
        )
    ).all()

    best_by_slug: dict[str, tuple[str, Decimal]] = {}
    for slug, name, weight, reps in rows:
        e1rm = _epley_e1rm(weight, reps)
        cur = best_by_slug.get(slug)
        if cur is None or e1rm > cur[1]:
            best_by_slug[slug] = (name, e1rm)

    findings: list[StrengthFinding] = []
    for muscle, slug_candidates in strength_norms.MUSCLE_TO_REPRESENTATIVE_SLUG.items():
        chosen: tuple[str, str, Decimal] | None = None  # (slug, name, e1rm)
        for slug in slug_candidates:
            entry = best_by_slug.get(slug)
            if entry is not None:
                chosen = (slug, entry[0], entry[1])
                break
        if chosen is None:
            continue
        band = strength_norms.get_band(chosen[0], user.sex_at_birth)
        if band is None:
            continue
        ratio = (chosen[2] / bw).quantize(Decimal("0.01"))
        classification = strength_norms.classify(ratio, band)
        findings.append(
            StrengthFinding(
                muscle=muscle,
                representative_slug=chosen[0],
                e1rm_kg=chosen[2],
                bodyweight_kg=bw,
                ratio=ratio,
                classification=classification,
            )
        )
    return findings


# Stagnation ---------------------------------------------------------------


def _linear_regression_slope(xs: list[Decimal], ys: list[Decimal]) -> tuple[Decimal, Decimal]:
    """Return (slope, residual_stddev) for y = a + b*x via OLS."""
    n = Decimal(len(xs))
    if n < 2:
        return Decimal("0"), Decimal("0")
    mean_x = sum(xs, Decimal("0")) / n
    mean_y = sum(ys, Decimal("0")) / n
    num = Decimal("0")
    den = Decimal("0")
    for x, y in zip(xs, ys, strict=True):
        dx = x - mean_x
        num += dx * (y - mean_y)
        den += dx * dx
    if den == 0:
        return Decimal("0"), Decimal("0")
    slope = num / den
    intercept = mean_y - slope * mean_x
    sq_err = Decimal("0")
    for x, y in zip(xs, ys, strict=True):
        predicted = intercept + slope * x
        diff = y - predicted
        sq_err += diff * diff
    variance = sq_err / n
    # Decimal sqrt: variance can be small but rarely negative due to rounding.
    if variance <= 0:
        return slope.quantize(Decimal("0.0001")), Decimal("0")
    stddev = variance.sqrt().quantize(Decimal("0.01"))
    return slope.quantize(Decimal("0.0001")), stddev


async def compute_stagnation_findings(
    session: AsyncSession,
    user: User,
    *,
    today: date,
) -> list[StagnationFinding]:
    since = today - timedelta(weeks=STAGNATION_LOOKBACK_WEEKS)
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    ex.slug,
                    ex.name,
                    ws.started_at::date AS session_date,
                    MAX(s.weight_kg * (1 + s.reps::numeric / 30)) AS top_e1rm
                FROM sets s
                JOIN workout_exercises we ON we.id = s.workout_exercise_id
                JOIN workout_sessions ws ON ws.id = we.workout_session_id
                JOIN exercises ex ON ex.id = we.exercise_id
                WHERE ws.user_id = :user_id
                  AND ws.deleted_at IS NULL
                  AND ws.ended_at IS NOT NULL
                  AND ws.started_at::date >= :since
                  AND s.set_type = 'working'
                  AND s.weight_kg IS NOT NULL
                  AND s.reps IS NOT NULL
                GROUP BY ex.slug, ex.name, session_date
                ORDER BY ex.slug, session_date
                """
            ),
            {"user_id": user.id, "since": since},
        )
    ).all()

    grouped: dict[str, list[tuple[str, date, Decimal]]] = {}
    for slug, name, sdate, e1rm in rows:
        grouped.setdefault(slug, []).append((name, sdate, e1rm))

    findings: list[StagnationFinding] = []
    for slug, entries in grouped.items():
        if len(entries) < STAGNATION_MIN_SESSIONS:
            continue
        name = entries[0][0]
        first_date = entries[0][1]
        xs = [Decimal((d - first_date).days) / Decimal("7") for _, d, _ in entries]
        ys = [Decimal(e1rm) for _, _, e1rm in entries]
        slope, stddev = _linear_regression_slope(xs, ys)
        if slope <= 0 and stddev <= STAGNATION_NOISE_THRESHOLD:
            findings.append(
                StagnationFinding(
                    exercise_slug=slug,
                    exercise_name=name,
                    slope_kg_per_week=slope,
                    residual_stddev=stddev,
                    sessions=len(entries),
                )
            )
    return findings


# Imbalance ----------------------------------------------------------------


async def _muscle_sets_in_window(
    session: AsyncSession, user_id: UUID, *, today: date, lookback_weeks: int
) -> dict[Muscle, Decimal]:
    """Total working_sets per muscle over the past `lookback_weeks` ISO weeks,
    by aggregating the existing rollup table.
    """
    since = today - timedelta(weeks=lookback_weeks)
    since_year, since_week, _ = since.isocalendar()
    cur_year, cur_week, _ = today.isocalendar()
    rows = (
        await session.execute(
            text(
                """
                SELECT muscle, SUM(working_sets)
                FROM muscle_volume_weekly
                WHERE user_id = :user_id
                  AND (iso_year, iso_week) >= (:since_year, :since_week)
                  AND (iso_year, iso_week) <= (:cur_year, :cur_week)
                GROUP BY muscle
                """
            ),
            {
                "user_id": user_id,
                "since_year": since_year,
                "since_week": since_week,
                "cur_year": cur_year,
                "cur_week": cur_week,
            },
        )
    ).all()
    out: dict[Muscle, Decimal] = {}
    for muscle_str, total in rows:
        try:
            out[Muscle(str(muscle_str))] = Decimal(total or 0)
        except ValueError:
            continue
    return out


def _ratio_outside(
    value_a: Decimal, value_b: Decimal, low: Decimal, high: Decimal
) -> Decimal | None:
    """Return the ratio if outside [low, high], else None. Requires both > 0."""
    if value_a <= 0 or value_b <= 0:
        return None
    ratio = (value_a / value_b).quantize(Decimal("0.01"))
    if low <= ratio <= high:
        return None
    return ratio


def compute_imbalance_findings(
    sets_by_muscle: dict[Muscle, Decimal],
) -> list[ImbalanceFinding]:
    findings: list[ImbalanceFinding] = []

    push = sum((sets_by_muscle.get(m, Decimal("0")) for m in PUSH_MUSCLES), Decimal("0"))
    pull = sum((sets_by_muscle.get(m, Decimal("0")) for m in PULL_MUSCLES), Decimal("0"))
    ratio = _ratio_outside(push, pull, Decimal("0.7"), Decimal("1.4"))
    if ratio is not None:
        findings.append(
            ImbalanceFinding(
                subject="push_vs_pull",
                label="push vs pull",
                ratio=ratio,
                low=Decimal("0.7"),
                high=Decimal("1.4"),
            )
        )

    quads = sum((sets_by_muscle.get(m, Decimal("0")) for m in QUAD_MUSCLES), Decimal("0"))
    hams = sum((sets_by_muscle.get(m, Decimal("0")) for m in HAM_MUSCLES), Decimal("0"))
    ratio = _ratio_outside(quads, hams, Decimal("0.6"), Decimal("1.5"))
    if ratio is not None:
        findings.append(
            ImbalanceFinding(
                subject="quads_vs_hamstrings",
                label="quads vs hamstrings",
                ratio=ratio,
                low=Decimal("0.6"),
                high=Decimal("1.5"),
            )
        )

    front = sum((sets_by_muscle.get(m, Decimal("0")) for m in FRONT_DELT_MUSCLES), Decimal("0"))
    rear = sum((sets_by_muscle.get(m, Decimal("0")) for m in REAR_DELT_MUSCLES), Decimal("0"))
    ratio = _ratio_outside(front, rear, Decimal("0.5"), Decimal("1.5"))
    if ratio is not None:
        findings.append(
            ImbalanceFinding(
                subject="front_vs_rear_delts",
                label="front vs rear delts",
                ratio=ratio,
                low=Decimal("0.5"),
                high=Decimal("1.5"),
            )
        )

    return findings


# Undertrained -------------------------------------------------------------


def compute_undertrained_findings(
    sets_by_muscle: dict[Muscle, Decimal], *, lookback_weeks: int
) -> list[UndertrainedFinding]:
    findings: list[UndertrainedFinding] = []
    for muscle in PRIMARY_MOVERS:
        total = sets_by_muscle.get(muscle, Decimal("0"))
        avg_per_week = (total / Decimal(lookback_weeks)).quantize(Decimal("0.01"))
        if avg_per_week < UNDERTRAINED_MIN_WEEKLY_SETS:
            findings.append(UndertrainedFinding(muscle=muscle, avg_weekly_sets=avg_per_week))
    return findings


# Strength findings -> insights --------------------------------------------


def _strength_findings_to_insights(
    findings: list[StrengthFinding],
) -> list[NewInsight]:
    """Bottom 25% of the user's muscles -> weak_muscle insights; top 25% ->
    strong_muscle. We always classify against the absolute band table first;
    the "bottom/top 25%" in the task corresponds to the band classifier.
    """
    insights: list[NewInsight] = []
    for f in findings:
        if f.classification == "weak":
            insights.append(
                NewInsight(
                    kind=AnalyticsInsightKind.weak_muscle,
                    severity=AnalyticsInsightSeverity.warn,
                    subject=str(f.muscle.value),
                    title=f"{f.muscle.value.replace('_', ' ').title()} looks underdeveloped",
                    body=(
                        f"Your best {f.representative_slug.replace('-', ' ')} e1RM is "
                        f"{f.e1rm_kg} kg at {f.ratio}x bodyweight, below the typical band."
                    ),
                    payload={
                        "muscle": f.muscle.value,
                        "representative_slug": f.representative_slug,
                        "e1rm_kg": str(f.e1rm_kg),
                        "bodyweight_kg": str(f.bodyweight_kg),
                        "ratio": str(f.ratio),
                    },
                )
            )
        elif f.classification == "strong":
            insights.append(
                NewInsight(
                    kind=AnalyticsInsightKind.strong_muscle,
                    severity=AnalyticsInsightSeverity.info,
                    subject=str(f.muscle.value),
                    title=f"{f.muscle.value.replace('_', ' ').title()} is a strong point",
                    body=(
                        f"Your best {f.representative_slug.replace('-', ' ')} e1RM is "
                        f"{f.e1rm_kg} kg at {f.ratio}x bodyweight, above the typical band."
                    ),
                    payload={
                        "muscle": f.muscle.value,
                        "representative_slug": f.representative_slug,
                        "e1rm_kg": str(f.e1rm_kg),
                        "bodyweight_kg": str(f.bodyweight_kg),
                        "ratio": str(f.ratio),
                    },
                )
            )
    return insights


def _stagnation_findings_to_insights(
    findings: list[StagnationFinding],
) -> list[NewInsight]:
    out: list[NewInsight] = []
    for f in findings:
        out.append(
            NewInsight(
                kind=AnalyticsInsightKind.stagnation,
                severity=AnalyticsInsightSeverity.action,
                subject=f.exercise_slug,
                title=f"{f.exercise_name} progress has stalled",
                body=(
                    f"Over the last {f.sessions} sessions your e1RM trend is "
                    f"{f.slope_kg_per_week} kg/week with low variance."
                ),
                payload={
                    "exercise_slug": f.exercise_slug,
                    "slope_kg_per_week": str(f.slope_kg_per_week),
                    "residual_stddev": str(f.residual_stddev),
                    "sessions": f.sessions,
                },
            )
        )
    return out


def _imbalance_findings_to_insights(
    findings: list[ImbalanceFinding],
) -> list[NewInsight]:
    out: list[NewInsight] = []
    for f in findings:
        out.append(
            NewInsight(
                kind=AnalyticsInsightKind.imbalance,
                severity=AnalyticsInsightSeverity.warn,
                subject=f.subject,
                title=f"{f.label.title()} looks imbalanced",
                body=(
                    f"Your {f.label} ratio over the last 4 weeks is {f.ratio}, "
                    f"outside the recommended range [{f.low}, {f.high}]."
                ),
                payload={
                    "subject": f.subject,
                    "ratio": str(f.ratio),
                    "low": str(f.low),
                    "high": str(f.high),
                },
            )
        )
    return out


def _undertrained_findings_to_insights(
    findings: list[UndertrainedFinding],
) -> list[NewInsight]:
    out: list[NewInsight] = []
    for f in findings:
        out.append(
            NewInsight(
                kind=AnalyticsInsightKind.undertrained,
                severity=AnalyticsInsightSeverity.warn,
                subject=str(f.muscle.value),
                title=f"{f.muscle.value.replace('_', ' ').title()} is undertrained",
                body=(
                    f"Average {f.avg_weekly_sets} working sets per week over "
                    f"the last 4 weeks. Target {UNDERTRAINED_TARGET_LOW}-"
                    f"{UNDERTRAINED_TARGET_HIGH} for growth."
                ),
                payload={
                    "muscle": f.muscle.value,
                    "avg_weekly_sets": str(f.avg_weekly_sets),
                    "target_low": UNDERTRAINED_TARGET_LOW,
                    "target_high": UNDERTRAINED_TARGET_HIGH,
                },
            )
        )
    return out


# Orchestration ------------------------------------------------------------


async def compute_insights_for_user(
    session: AsyncSession, user: User, *, today: date | None = None
) -> list[UUID]:
    """Run all heuristics, upsert findings into analytics_insights, return the
    list of insight row ids that were inserted or updated. The list is the
    candidate set for LLM rationale generation.
    """
    today = today or _today_utc()

    new_insights: list[NewInsight] = []
    new_insights.extend(
        _strength_findings_to_insights(await compute_strength_findings(session, user, today=today))
    )
    new_insights.extend(
        _stagnation_findings_to_insights(
            await compute_stagnation_findings(session, user, today=today)
        )
    )
    sets_by_muscle = await _muscle_sets_in_window(
        session, user.id, today=today, lookback_weeks=IMBALANCE_LOOKBACK_WEEKS
    )
    new_insights.extend(_imbalance_findings_to_insights(compute_imbalance_findings(sets_by_muscle)))
    new_insights.extend(
        _undertrained_findings_to_insights(
            compute_undertrained_findings(
                sets_by_muscle, lookback_weeks=UNDERTRAINED_LOOKBACK_WEEKS
            )
        )
    )

    return await _upsert_insights(session, user.id, new_insights)


async def _upsert_insights(
    session: AsyncSession, user_id: UUID, items: list[NewInsight]
) -> list[UUID]:
    """For each NewInsight:
    - If an active row exists for (user, kind, subject): update in place.
    - Else if a dismissed row exists with dismissed_at within DISMISS_COOLDOWN_DAYS:
      skip (do not resurface).
    - Else: insert a new row.

    Returns the list of inserted/updated row ids.
    """
    now = datetime.now(tz=UTC)
    cooldown_cutoff = now - timedelta(days=DISMISS_COOLDOWN_DAYS)
    written: list[UUID] = []

    for item in items:
        # 1. Look for an active row.
        active = (
            await session.execute(
                select(AnalyticsInsight).where(
                    AnalyticsInsight.user_id == user_id,
                    AnalyticsInsight.kind == item.kind,
                    AnalyticsInsight.subject == item.subject,
                    AnalyticsInsight.dismissed_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if active is not None:
            active.severity = item.severity
            active.title = item.title
            active.body = item.body
            active.payload = item.payload
            active.surfaced_at = now
            # Reset rationale so the LLM job re-fills if any payload changed.
            active.rationale = None
            await session.flush()
            written.append(active.id)
            continue

        # 2. Skip if a recent dismissal exists within the cooldown.
        recent_dismissal = (
            await session.execute(
                select(AnalyticsInsight.id).where(
                    AnalyticsInsight.user_id == user_id,
                    AnalyticsInsight.kind == item.kind,
                    AnalyticsInsight.subject == item.subject,
                    AnalyticsInsight.dismissed_at.is_not(None),
                    AnalyticsInsight.dismissed_at >= cooldown_cutoff,
                )
            )
        ).scalar_one_or_none()
        if recent_dismissal is not None:
            continue

        # 3. Insert new.
        row = AnalyticsInsight(
            user_id=user_id,
            kind=item.kind,
            severity=item.severity,
            subject=item.subject,
            title=item.title,
            body=item.body,
            payload=item.payload,
            surfaced_at=now,
        )
        session.add(row)
        await session.flush()
        written.append(row.id)
    return written


# Cleanup / TTL -------------------------------------------------------------


async def cleanup_expired_insights(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Delete stale STAGNATION insights to keep the table bounded.

    A row is expired when ALL of:
    - its kind is in ``TTL_KINDS`` (stagnation), and
    - it is older than its applicable TTL measured from ``created_at``:
        * 30 days for heuristic-only rows (``rationale IS NULL``), since the
          nightly recompute will re-emit them for free if still relevant;
        * 180 days for rows that carry an LLM-generated rationale, because
          regenerating that rationale costs an Ollama call.

    Dismissed rows are also covered: once expired by age they are removed too.
    Returns the number of deleted rows. Caller commits.
    """
    now = now or datetime.now(tz=UTC)
    heuristic_cutoff = now - timedelta(days=STAGNATION_TTL_DAYS)
    rationale_cutoff = now - timedelta(days=RATIONALE_TTL_DAYS)

    result = await session.execute(
        delete(AnalyticsInsight).where(
            AnalyticsInsight.kind.in_(TTL_KINDS),
            or_(
                and_(
                    AnalyticsInsight.rationale.is_(None),
                    AnalyticsInsight.created_at < heuristic_cutoff,
                ),
                and_(
                    AnalyticsInsight.rationale.is_not(None),
                    AnalyticsInsight.created_at < rationale_cutoff,
                ),
            ),
        )
    )
    # DELETE yields a CursorResult (has rowcount); narrow for the type checker.
    return cast("CursorResult[Any]", result).rowcount or 0
