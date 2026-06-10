from datetime import date as date_cls
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.enums import MealType
from app.models.user import User
from app.schemas.meal import (
    DayMacros,
    DayPerMeal,
    DaySummaryResponse,
    MealCreate,
    MealItemCreate,
    MealItemResponse,
    MealItemUpdate,
    MealList,
    MealResponse,
    MealUpdate,
)
from app.services import meals as meals_svc

router = APIRouter(tags=["meals"])


# ---------------------------------------------------------------------------
# Meals CRUD
# ---------------------------------------------------------------------------


@router.post("/meals", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
async def create_meal(
    payload: MealCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealResponse:
    record = await meals_svc.create_meal(
        session,
        current_user,
        eaten_at=payload.eaten_at,
        meal_type=payload.meal_type,
        notes=payload.notes,
    )
    await session.commit()
    full = await meals_svc.get_meal(session, current_user, record.id)
    return MealResponse.model_validate(full)


@router.get("/meals", response_model=MealList)
async def list_meals(
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    meal_type: MealType | None = Query(default=None),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealList:
    rows = await meals_svc.list_meals(
        session, current_user, from_dt=from_dt, to_dt=to_dt, meal_type=meal_type
    )
    return MealList(items=[MealResponse.model_validate(r) for r in rows])


@router.get("/meals/{meal_id}", response_model=MealResponse)
async def get_meal(
    meal_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealResponse:
    record = await meals_svc.get_meal(session, current_user, meal_id)
    return MealResponse.model_validate(record)


@router.patch("/meals/{meal_id}", response_model=MealResponse)
async def update_meal(
    meal_id: UUID,
    payload: MealUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealResponse:
    await meals_svc.update_meal(
        session, current_user, meal_id, payload.model_dump(exclude_unset=True)
    )
    await session.commit()
    full = await meals_svc.get_meal(session, current_user, meal_id)
    return MealResponse.model_validate(full)


@router.delete("/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await meals_svc.soft_delete_meal(session, current_user, meal_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Meal items
# ---------------------------------------------------------------------------


@router.post(
    "/meals/{meal_id}/items",
    response_model=MealItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_meal_item(
    meal_id: UUID,
    payload: MealItemCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealItemResponse:
    record = await meals_svc.add_item(
        session,
        current_user,
        meal_id,
        food_id=payload.food_id,
        grams=payload.grams,
    )
    await session.commit()
    return MealItemResponse.model_validate(record)


@router.patch("/meal-items/{item_id}", response_model=MealItemResponse)
async def update_meal_item(
    item_id: UUID,
    payload: MealItemUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealItemResponse:
    record = await meals_svc.update_item(
        session,
        current_user,
        item_id,
        grams=payload.grams,
        food_id=payload.food_id,
    )
    await session.commit()
    return MealItemResponse.model_validate(record)


@router.delete("/meal-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_item(
    item_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await meals_svc.delete_item(session, current_user, item_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------


@router.get("/nutrition/day", response_model=DaySummaryResponse)
async def nutrition_day(
    day: date_cls = Query(..., alias="date"),
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> DaySummaryResponse:
    data = await meals_svc.daily_summary(
        session, current_user, day=day, tz_offset_minutes=tz_offset_minutes
    )
    return DaySummaryResponse(
        date=data["date"],
        totals=DayMacros(**data["totals"]),
        per_meal=[
            DayPerMeal(
                meal_id=m["meal_id"],
                meal_type=m["meal_type"],
                eaten_at=m["eaten_at"],
                totals=DayMacros(**m["totals"]),
                items=[MealItemResponse.model_validate(i) for i in m["items"]],
            )
            for m in data["per_meal"]
        ],
    )
