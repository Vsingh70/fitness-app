"""Build a full account-data export bundle for a single user.

For compliance + portability: returns every row the user owns across the
primary domains, including soft-deleted rows, since the user still owns that
data and a portability export should be complete.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.body_metric import BodyMetric
from app.models.meal import Meal
from app.models.program import Program, ProgramDay
from app.models.user import User
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet
from app.schemas.export import ExportBundle


async def build_export_bundle(session: AsyncSession, user: User) -> ExportBundle:
    sessions_result = await session.execute(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user.id)
        .options(
            selectinload(WorkoutSession.workout_exercises).options(
                selectinload(WorkoutExercise.sets).selectinload(WorkoutSet.segments),
                selectinload(WorkoutExercise.exercise),
            )
        )
        .order_by(WorkoutSession.started_at)
    )
    workout_sessions = list(sessions_result.scalars().all())

    meals_result = await session.execute(
        select(Meal)
        .where(Meal.user_id == user.id)
        .options(selectinload(Meal.items))
        .order_by(Meal.eaten_at)
    )
    meals = list(meals_result.scalars().all())

    body_metrics_result = await session.execute(
        select(BodyMetric).where(BodyMetric.user_id == user.id).order_by(BodyMetric.recorded_at)
    )
    body_metrics = list(body_metrics_result.scalars().all())

    programs_result = await session.execute(
        select(Program)
        .where(Program.owner_id == user.id)
        .options(selectinload(Program.days).selectinload(ProgramDay.exercises))
        .order_by(Program.created_at)
    )
    programs = list(programs_result.scalars().all())

    return ExportBundle.model_validate(
        {
            "exported_at": datetime.now(UTC),
            "user": user,
            "workout_sessions": workout_sessions,
            "meals": meals,
            "body_metrics": body_metrics,
            "programs": programs,
        }
    )
