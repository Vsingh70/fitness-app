from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.schemas.integrations_fitbit import FitbitPushResponse
from app.schemas.workout import (
    SetCreate,
    SetResponse,
    SetUpdate,
    WorkoutExerciseCreate,
    WorkoutExerciseReorder,
    WorkoutExerciseResponse,
    WorkoutExerciseUpdate,
    WorkoutSessionCreate,
    WorkoutSessionList,
    WorkoutSessionListItem,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)
from app.services import workouts as svc
from app.services.analytics import enqueue as analytics_enqueue
from app.services.idempotency import (
    get_cached_idempotent,
    hash_payload,
    save_idempotent,
)

router = APIRouter(tags=["workouts"])


def _serialize_session(record: object) -> WorkoutSessionResponse:
    return WorkoutSessionResponse.model_validate(record)


async def _replay_or_run(
    session: AsyncSession,
    user: User,
    request: Request,
    body: Any,
    handler: Callable[[], Awaitable[tuple[int, dict[str, Any]]]],
) -> tuple[int, dict[str, Any] | None]:
    """Idempotency wrapper. Returns (status_code, body). Body may be None for 204s."""
    idem_key = request.headers.get("Idempotency-Key")
    route = request.url.path

    if idem_key:
        request_hash = hash_payload(body.model_dump(mode="json") if body is not None else None)
        cached = await get_cached_idempotent(session, user.id, idem_key, route, request_hash)
        if cached is not None:
            return cached

    status_code, response_body = await handler()

    if idem_key:
        await save_idempotent(
            session, user.id, idem_key, route, request_hash, status_code, response_body
        )

    return status_code, response_body


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.post(
    "/workout-sessions",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workout_session(
    payload: WorkoutSessionCreate,
    request: Request,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Response:
    async def run() -> tuple[int, dict[str, Any]]:
        record = await svc.create_session(session, current_user, payload)
        # Re-fetch with relationships eagerly loaded for the response shape.
        full = await svc.get_session_full(session, current_user, record.id)
        await session.commit()
        body = _serialize_session(full).model_dump(mode="json")
        return status.HTTP_201_CREATED, body

    status_code, body = await _replay_or_run(session, current_user, request, payload, run)
    return Response(content=_json(body), status_code=status_code, media_type="application/json")


@router.get("/workout-sessions", response_model=WorkoutSessionList)
async def list_workout_sessions(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionList:
    items, next_cursor = await svc.list_sessions(
        session, current_user, from_dt=from_, to_dt=to, limit=limit, cursor=cursor
    )
    return WorkoutSessionList(
        items=[WorkoutSessionListItem.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )


@router.get("/workout-sessions/{session_id}", response_model=WorkoutSessionResponse)
async def get_workout_session(
    session_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    record = await svc.get_session_full(session, current_user, session_id)
    return _serialize_session(record)


@router.patch("/workout-sessions/{session_id}", response_model=WorkoutSessionResponse)
async def patch_workout_session(
    session_id: UUID,
    payload: WorkoutSessionUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    await svc.update_session(session, current_user, session_id, payload)
    full = await svc.get_session_full(session, current_user, session_id)
    await session.commit()
    return _serialize_session(full)


@router.post("/workout-sessions/{session_id}/finish", response_model=WorkoutSessionResponse)
async def finish_workout_session(
    session_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    result = await svc.finish_session(session, current_user, session_id)
    full = await svc.get_session_full(session, current_user, session_id)
    await session.commit()

    # Post-commit: enqueue rationale generation, volume rollup, and (if
    # connected + auto-push) a Fitbit activity push. Workers read the
    # committed rows; on Redis outage the helpers log and continue.
    from app.services.ai import rationale_job
    from app.services.fitbit_push_enqueue import enqueue_push as enqueue_fitbit_push

    for rec_id in result.rec_ids:
        await rationale_job.enqueue_for_recommendation(rec_id)
    await analytics_enqueue.enqueue_rollup(
        current_user.id, result.affected_iso_year, result.affected_iso_week
    )
    if result.should_push_to_fitbit:
        await enqueue_fitbit_push(session_id)

    return _serialize_session(full)


@router.post(
    "/workout-sessions/{session_id}/push-to-fitbit",
    response_model=FitbitPushResponse,
)
async def push_workout_session_to_fitbit(
    session_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FitbitPushResponse:
    # Authorize ownership via the standard service helper, then push.
    await svc.get_session_full(session, current_user, session_id)
    from app.services import fitbit_push

    result = await fitbit_push.push_session_to_fitbit(session, session_id)
    await session.commit()
    return FitbitPushResponse(
        pushed=result.pushed,
        skipped_reason=result.skipped_reason,
        fitbit_log_id=result.fitbit_log_id,
    )


@router.delete(
    "/workout-sessions/{session_id}/fitbit-link",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_fitbit_link(
    session_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    record = await svc.get_session_full(session, current_user, session_id)
    from app.services import fitbit_push

    await fitbit_push.clear_fitbit_link(session, record)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/workout-sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_session(
    session_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.soft_delete_session(session, current_user, session_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/workout-sessions/{session_id}/restore", response_model=WorkoutSessionResponse)
async def restore_workout_session(
    session_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionResponse:
    await svc.restore_session(session, current_user, session_id)
    full = await svc.get_session_full(session, current_user, session_id)
    await session.commit()
    return _serialize_session(full)


# ---------------------------------------------------------------------------
# Workout exercises
# ---------------------------------------------------------------------------


@router.post(
    "/workout-sessions/{session_id}/exercises",
    response_model=WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workout_exercise(
    session_id: UUID,
    payload: WorkoutExerciseCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutExerciseResponse:
    record = await svc.add_exercise(session, current_user, session_id, payload)
    await session.commit()
    await session.refresh(record, attribute_names=["sets"])
    return WorkoutExerciseResponse.model_validate(record)


@router.patch("/workout-exercises/{workout_exercise_id}", response_model=WorkoutExerciseResponse)
async def patch_workout_exercise(
    workout_exercise_id: UUID,
    payload: WorkoutExerciseUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutExerciseResponse:
    record = await svc.update_workout_exercise(session, current_user, workout_exercise_id, payload)
    await session.commit()
    await session.refresh(record, attribute_names=["sets"])
    return WorkoutExerciseResponse.model_validate(record)


@router.delete("/workout-exercises/{workout_exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workout_exercise(
    workout_exercise_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_workout_exercise(session, current_user, workout_exercise_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/workout-exercises/{workout_exercise_id}/reorder",
    response_model=WorkoutExerciseResponse,
)
async def reorder_workout_exercise(
    workout_exercise_id: UUID,
    payload: WorkoutExerciseReorder,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkoutExerciseResponse:
    record = await svc.reorder_workout_exercise(
        session, current_user, workout_exercise_id, payload.position
    )
    await session.commit()
    await session.refresh(record, attribute_names=["sets"])
    return WorkoutExerciseResponse.model_validate(record)


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------


@router.post(
    "/workout-exercises/{workout_exercise_id}/sets",
    response_model=SetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workout_set(
    workout_exercise_id: UUID,
    payload: SetCreate,
    request: Request,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Response:
    async def run() -> tuple[int, dict[str, Any]]:
        record = await svc.add_set(session, current_user, workout_exercise_id, payload)
        await session.commit()
        body = SetResponse.model_validate(record).model_dump(mode="json")
        return status.HTTP_201_CREATED, body

    status_code, body = await _replay_or_run(session, current_user, request, payload, run)
    return Response(content=_json(body), status_code=status_code, media_type="application/json")


@router.patch("/sets/{set_id}", response_model=SetResponse)
async def patch_set(
    set_id: UUID,
    payload: SetUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> SetResponse:
    record = await svc.update_set(session, current_user, set_id, payload)
    await session.commit()
    await analytics_enqueue.enqueue_rollup_for_set(session, set_id)
    return SetResponse.model_validate(record)


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_set(
    set_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    # Snapshot the session id BEFORE deleting the set so we can roll up.
    session_id = (
        await session.execute(
            select(WorkoutSession.id)
            .join(WorkoutExercise, WorkoutExercise.workout_session_id == WorkoutSession.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(WorkoutSet.id == set_id)
        )
    ).scalar_one_or_none()

    await svc.delete_set(session, current_user, set_id)
    await session.commit()

    if session_id is not None:
        await analytics_enqueue.enqueue_rollup_for_session(session, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Internal: small JSON helper so we can build cached responses byte-identically.
# ---------------------------------------------------------------------------


def _json(payload: Any) -> bytes:
    import json

    return json.dumps(payload, separators=(",", ":"), default=str).encode()
