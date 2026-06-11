from datetime import UTC, datetime
from datetime import date as date_cls
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.meal import (
    ActivePlanProgress,
    DayMacros,
    MealPlanCreate,
    MealPlanList,
    MealPlanResponse,
    MealPlanTargets,
    MealPlanUpdate,
    RemainingMacros,
)
from app.services import meal_plans as plans_svc
from app.services import nutrition_targets

router = APIRouter(tags=["meal-plans"])


@router.post("/meal-plans", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: MealPlanCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanResponse:
    record = await plans_svc.create_plan(
        session,
        current_user,
        name=payload.name,
        target_kcal=payload.target_kcal,
        target_protein_g=payload.target_protein_g,
        target_carbs_g=payload.target_carbs_g,
        target_fat_g=payload.target_fat_g,
        target_fiber_g=payload.target_fiber_g,
        days=payload.days,
    )
    await session.commit()
    return MealPlanResponse.model_validate(record)


@router.get("/meal-plans", response_model=MealPlanList)
async def list_plans(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanList:
    rows = await plans_svc.list_plans(session, current_user)
    return MealPlanList(items=[MealPlanResponse.model_validate(r) for r in rows])


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
    return MealPlanResponse.model_validate(record)


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
    return MealPlanResponse.model_validate(record)


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
    if data is None:
        return None
    return ActivePlanProgress(
        plan=MealPlanResponse.model_validate(data["plan"]),
        consumed=DayMacros(**data["consumed"]),
        remaining=RemainingMacros(**data["remaining"]),
        date=data["date"],
    )


@router.get("/nutrition/targets", response_model=MealPlanTargets)
async def get_targets(
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealPlanTargets:
    """Return active-plan targets if one exists, otherwise Mifflin-St Jeor
    defaults derived from profile + latest body weight.
    """
    plan = await plans_svc.get_active_plan(session, current_user)
    if plan is not None:
        return MealPlanTargets(
            target_kcal=plan.target_kcal,
            target_protein_g=plan.target_protein_g,
            target_carbs_g=plan.target_carbs_g,
            target_fat_g=plan.target_fat_g,
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
