from datetime import UTC, datetime
from datetime import date as date_cls
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.meal import (
    ActivePlanProgress,
    DayMacros,
    MealPlanCreate,
    MealPlanDayCreate,
    MealPlanDayPatch,
    MealPlanDayResponse,
    MealPlanItemCreate,
    MealPlanItemPatch,
    MealPlanList,
    MealPlanMealCreate,
    MealPlanMealPatch,
    MealPlanResponse,
    MealPlanTargets,
    MealPlanUpdate,
    MealResponse,
    RemainingMacros,
    ResolvedDay,
)
from app.services import meal_plans as plans_svc
from app.services import meals as meals_svc
from app.services import nutrition_targets

router = APIRouter(tags=["meal-plans"])


def _plan_out(record: object) -> MealPlanResponse:
    return MealPlanResponse.model_validate(plans_svc.serialize_plan(record))  # type: ignore[arg-type]


@router.post("/meal-plans", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: MealPlanCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.create_plan(session, current_user, payload)
    await session.commit()
    return _plan_out(record)


@router.get("/meal-plans", response_model=MealPlanList)
async def list_plans(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanList:
    rows = await plans_svc.list_plans(session, current_user)
    return MealPlanList(items=[_plan_out(r) for r in rows])


@router.get("/meal-plans/active", response_model=ActivePlanProgress | None)
async def get_active_plan(
    day: date_cls | None = Query(default=None, alias="date"),
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ActivePlanProgress | None:
    today = day or datetime.now(tz=UTC).date()
    data = await plans_svc.active_with_progress(
        session, current_user, day=today, tz_offset_minutes=tz_offset_minutes
    )
    # resolve_day may flag needs_week_review; persist that.
    await session.commit()
    if data is None:
        return None
    return ActivePlanProgress(
        plan=_plan_out(data["plan"]),
        resolved_day=ResolvedDay.model_validate(data["resolved_day"]),
        consumed=DayMacros(**data["consumed"]),
        remaining=RemainingMacros(**data["remaining"]),
        date=data["date"],
    )


@router.get("/meal-plans/{plan_id}", response_model=MealPlanResponse)
async def get_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.get_plan(session, current_user, plan_id)
    return _plan_out(record)


@router.get("/meal-plans/{plan_id}/day", response_model=ResolvedDay)
async def get_plan_day(
    plan_id: UUID,
    day: date_cls = Query(alias="date"),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ResolvedDay:
    record = await plans_svc.get_plan(session, current_user, plan_id)
    resolved = await plans_svc.resolve_day(session, current_user, record, day)
    await session.commit()
    return ResolvedDay.model_validate(resolved)


@router.patch("/meal-plans/{plan_id}", response_model=MealPlanResponse)
async def update_plan(
    plan_id: UUID,
    payload: MealPlanUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.update_plan(
        session, current_user, plan_id, payload.model_dump(exclude_unset=True)
    )
    await session.commit()
    return _plan_out(record)


@router.delete("/meal-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await plans_svc.soft_delete_plan(session, current_user, plan_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/meal-plans/{plan_id}/activate", response_model=MealPlanResponse)
async def activate_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.activate_plan(session, current_user, plan_id)
    await session.commit()
    return _plan_out(record)


# --- nested day templates --------------------------------------------------


@router.post(
    "/meal-plans/{plan_id}/days",
    response_model=MealPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_day(
    plan_id: UUID,
    payload: MealPlanDayCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.add_day(session, current_user, plan_id, payload)
    await session.commit()
    return _plan_out(record)


@router.patch("/meal-plan-days/{day_id}", response_model=MealPlanDayResponse)
async def update_day(
    day_id: UUID,
    payload: MealPlanDayPatch,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanDayResponse:
    record = await plans_svc.update_day(
        session, current_user, day_id, payload.model_dump(exclude_unset=True)
    )
    await session.commit()
    day = next(d for d in record.day_templates if d.id == day_id)
    return MealPlanDayResponse.model_validate(plans_svc.serialize_day(record, day))


@router.delete("/meal-plan-days/{day_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_day(
    day_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await plans_svc.delete_day(session, current_user, day_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- nested meals ----------------------------------------------------------


@router.post(
    "/meal-plan-days/{day_id}/meals",
    response_model=MealPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_meal(
    day_id: UUID,
    payload: MealPlanMealCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.add_meal(session, current_user, day_id, payload)
    await session.commit()
    return _plan_out(record)


@router.patch("/meal-plan-meals/{meal_id}", response_model=MealPlanResponse)
async def update_meal(
    meal_id: UUID,
    payload: MealPlanMealPatch,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.update_meal(
        session, current_user, meal_id, payload.model_dump(exclude_unset=True)
    )
    await session.commit()
    return _plan_out(record)


@router.delete("/meal-plan-meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await plans_svc.delete_meal(session, current_user, meal_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/meal-plans/{plan_id}/meals/{planned_meal_id}/complete",
    response_model=MealResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_planned_meal(
    plan_id: UUID,
    planned_meal_id: UUID,
    day: date_cls = Query(alias="date"),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealResponse:
    """Materialize a planned meal into a logged meal for ``date``.

    Idempotent per (planned meal, date): re-completing returns the existing
    logged meal instead of creating a duplicate.
    """
    record = await meals_svc.complete_planned_meal(
        session, current_user, plan_id, planned_meal_id, day=day
    )
    await session.commit()
    full = await meals_svc.get_meal(session, current_user, record.id)
    return MealResponse.model_validate(full)


# --- nested items ----------------------------------------------------------


@router.post(
    "/meal-plan-meals/{meal_id}/items",
    response_model=MealPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    meal_id: UUID,
    payload: MealPlanItemCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.add_item(session, current_user, meal_id, payload)
    await session.commit()
    return _plan_out(record)


@router.patch("/meal-plan-items/{item_id}", response_model=MealPlanResponse)
async def update_item(
    item_id: UUID,
    payload: MealPlanItemPatch,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.update_item(session, current_user, item_id, payload)
    await session.commit()
    return _plan_out(record)


@router.delete("/meal-plan-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await plans_svc.delete_item(session, current_user, item_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- nutrition targets (active plan defaults or Mifflin-St Jeor) -----------


@router.get("/nutrition/targets", response_model=MealPlanTargets)
async def get_targets(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanTargets:
    """Return active-plan targets if one exists, otherwise Mifflin-St Jeor
    defaults derived from profile + latest body weight.
    """
    plan = await plans_svc.get_active_plan(session, current_user)
    if plan is not None and plan.target_kcal is not None:
        return MealPlanTargets(
            target_kcal=plan.target_kcal,
            target_protein_g=plan.target_protein_g or Decimal("0"),
            target_carbs_g=plan.target_carbs_g or Decimal("0"),
            target_fat_g=plan.target_fat_g or Decimal("0"),
        )
    defaults = await nutrition_targets.derive_default_targets(session, current_user)
    if defaults is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=409,
            detail=(
                "Missing profile data: need height_cm, birthdate, and at least one "
                "body_metrics weight entry to derive default targets."
            ),
        )
    return MealPlanTargets(
        target_kcal=defaults.target_kcal,
        target_protein_g=defaults.target_protein_g,
        target_carbs_g=defaults.target_carbs_g,
        target_fat_g=defaults.target_fat_g,
    )
