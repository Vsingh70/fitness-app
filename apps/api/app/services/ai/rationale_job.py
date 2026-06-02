"""Glue between persisted recommendations and the rationale generator.

The orchestrator calls `enqueue_for_recommendation` after writing a rec; the
ARQ worker runs `rationalize_recommendation` which loads the row, calls
`generate_rationale`, and writes the result back. Decoupling means session
finalize does not block on LLM latency.

In tests we monkeypatch the enqueue helper to run the job inline so we can
assert on the final stored rationale.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis, create_pool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.exercise import Exercise
from app.models.recommendation import Recommendation
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.services.ai.rationales import (
    RationaleContext,
    RationaleRequest,
    generate_rationale,
)

ARQ_TASK_NAME = "rationalize_recommendation"


async def _build_request(session: AsyncSession, rec: Recommendation) -> RationaleRequest:
    exercise = (
        await session.execute(select(Exercise).where(Exercise.id == rec.exercise_id))
    ).scalar_one()

    last_three = await _recent_session_summaries(
        session, user_id=rec.user_id, exercise_id=rec.exercise_id, limit=3
    )

    template_vars = _template_variables_from_rec(rec)

    return RationaleRequest(
        rationale_key=rec.rationale_key or "",
        next_weight_kg=rec.suggested_weight_kg,
        next_reps_low=rec.suggested_reps_low,
        next_reps_high=rec.suggested_reps_high,
        is_deload=bool(rec.payload.get("is_deload")) if rec.payload else False,
        template_variables=template_vars,
        context=RationaleContext(
            exercise_name=exercise.name,
            prior_weight_kg=_decimal_from_payload(rec.payload.get("prior_weight_kg"))
            if rec.payload
            else None,
            last_three_sessions=last_three,
        ),
    )


def _decimal_from_payload(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _template_variables_from_rec(rec: Recommendation) -> dict[str, str]:
    """Build the {var} dict consumed by the fallback templates.

    The current set of supported variables:
    - increment_kg: difference between suggested and prior weight (positive).
    - reps_low / reps_high: the suggested rep targets.
    """
    out: dict[str, str] = {}
    if rec.suggested_reps_low is not None:
        out["reps_low"] = str(rec.suggested_reps_low)
    if rec.suggested_reps_high is not None:
        out["reps_high"] = str(rec.suggested_reps_high)
    prior = _decimal_from_payload(rec.payload.get("prior_weight_kg")) if rec.payload else None
    if rec.suggested_weight_kg is not None and prior is not None:
        delta = rec.suggested_weight_kg - prior
        if delta != 0:
            out["increment_kg"] = f"{abs(delta):.2f}"
    return out


async def _recent_session_summaries(
    session: AsyncSession,
    *,
    user_id: UUID,
    exercise_id: UUID,
    limit: int,
) -> list[str]:
    """Short human-readable summary of the user's last N sessions for an
    exercise. Format per line: "YYYY-MM-DD: top-set <weight>kg x <reps>".
    """
    rows = (
        await session.execute(
            select(WorkoutExercise.id, WorkoutSession.ended_at)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutExercise.exercise_id == exercise_id,
                WorkoutSession.ended_at.is_not(None),
                WorkoutSession.deleted_at.is_(None),
            )
            .order_by(WorkoutSession.ended_at.desc())
            .limit(limit)
        )
    ).all()
    out: list[str] = []
    for we_id, ended_at in rows:
        sets = (
            (
                await session.execute(
                    select(WorkoutSet).where(WorkoutSet.workout_exercise_id == we_id)
                )
            )
            .scalars()
            .all()
        )
        working = [s for s in sets if s.set_type.value == "working" and s.weight_kg is not None]
        if not working:
            continue
        top_weight = max(s.weight_kg for s in working if s.weight_kg is not None)
        reps_at_top = [s.reps for s in working if s.weight_kg == top_weight and s.reps is not None]
        if not reps_at_top:
            continue
        date_str = ended_at.date().isoformat()
        out.append(f"{date_str}: top-set {top_weight}kg x {max(reps_at_top)}")
    return out


async def rationalize_recommendation_inline(session: AsyncSession, rec_id: UUID) -> str | None:
    """Load a rec, generate a rationale, persist it. Returns the stored
    rationale string (or None if the rec disappeared).
    """
    rec = (
        await session.execute(select(Recommendation).where(Recommendation.id == rec_id))
    ).scalar_one_or_none()
    if rec is None:
        return None
    req = await _build_request(session, rec)
    rationale = await generate_rationale(req, user_id=rec.user_id)
    rec.rationale = rationale
    await session.flush()
    return rationale


async def rationalize_recommendation(ctx: dict[str, Any], rec_id: str) -> str | None:
    """ARQ task entrypoint. `ctx` is provided by arq; rec_id is a string UUID."""
    from app.db import get_sessionmaker

    sm = get_sessionmaker()
    async with sm() as session:
        result = await rationalize_recommendation_inline(session, UUID(rec_id))
        await session.commit()
        return result


# ---------------------------------------------------------------------------
# Enqueue helper. Tests override this to run inline.
# ---------------------------------------------------------------------------


async def _enqueue_via_arq(rec_id: UUID) -> None:
    redis: ArqRedis = await create_pool_for_enqueue()
    try:
        await redis.enqueue_job(ARQ_TASK_NAME, str(rec_id))
    finally:
        await redis.close(close_connection_pool=True)


async def create_pool_for_enqueue() -> ArqRedis:
    from arq.connections import RedisSettings

    settings = RedisSettings.from_dsn(get_settings().redis_url)
    return await create_pool(settings)


# Module-level callable; tests reassign this to a sync-or-inline helper.
async def enqueue_for_recommendation(rec_id: UUID) -> None:
    """Enqueue the ARQ job. Best-effort: a Redis outage logs and continues
    (the rec still gets the templated fallback when the user reads it via the
    API, since the rationale column is null and the renderer can fall back).
    """
    import logging

    log = logging.getLogger(__name__)
    try:
        await _enqueue_via_arq(rec_id)
    except Exception as exc:
        log.warning("rationale_enqueue_failed", extra={"rec_id": str(rec_id), "error": repr(exc)})
