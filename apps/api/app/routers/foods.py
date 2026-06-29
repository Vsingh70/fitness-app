from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.enums import FoodSource
from app.models.user import User
from app.schemas.food import (
    FoodCreate,
    FoodList,
    FoodResponse,
    FoodUpdate,
    ParsedFoodNutrition,
    ParseFoodUrlRequest,
    RecentFoodList,
    RecentFoodResponse,
)
from app.services import food_url_parse
from app.services import foods as svc
from app.services import meals as meals_svc
from app.services.rate_limit import check_user_limit

router = APIRouter(tags=["foods"])


@router.get("/foods/search", response_model=FoodList)
async def search_foods(
    q: str = Query(..., min_length=1),
    source: FoodSource | None = Query(default=None),
    min_protein_per_100g: Decimal | None = Query(default=None, ge=0),
    limit: int = Query(default=svc.DEFAULT_LIMIT, ge=1, le=svc.MAX_LIMIT),
    cursor: str | None = Query(default=None),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FoodList:
    rows, next_cursor = await svc.search_foods(
        session,
        current_user,
        q=q,
        source=source,
        min_protein_per_100g=min_protein_per_100g,
        limit=limit,
        cursor=cursor,
    )
    # The live fallback may have cached freshly-fetched foods; persist them so the
    # next search is local. A no-op when nothing was cached.
    await session.commit()
    return FoodList(
        items=[FoodResponse.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )


@router.post("/foods/parse-url", response_model=ParsedFoodNutrition)
async def parse_food_url(
    body: ParseFoodUrlRequest,
    current_user: User = Depends(get_current_user),
) -> ParsedFoodNutrition:
    """Parse nutrition from a food/recipe webpage to prefill the manual-add form.

    Reads schema.org structured data (no AI). Auth-gated and per-user
    rate-limited so it isn't abused as an outbound fetch proxy; the parser itself
    rejects private/loopback URLs (SSRF guard).
    """
    await check_user_limit(current_user.id)
    return await food_url_parse.parse_food_url(body.url)


@router.get("/foods/recent", response_model=RecentFoodList)
async def recent_foods(
    limit: int = Query(
        default=meals_svc.RECENT_FOODS_DEFAULT_LIMIT,
        ge=1,
        le=meals_svc.RECENT_FOODS_MAX_LIMIT,
    ),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> RecentFoodList:
    """The user's most-recently-and-frequently logged foods, for one-tap
    "recent chips". Each item carries the most recent amount/unit + macros so the
    client can re-log it in one tap. Excludes soft-deleted meals."""
    rows = await meals_svc.recent_foods(session, current_user, limit=limit)
    return RecentFoodList(items=[RecentFoodResponse(**row) for row in rows])


@router.get("/foods/barcode/{barcode}", response_model=FoodResponse)
async def lookup_barcode(
    barcode: str,
    session: AsyncSession = Depends(db_session),
    _current_user: User = Depends(get_current_user),
) -> FoodResponse:
    record = await svc.lookup_barcode(session, barcode)
    await session.commit()
    return FoodResponse.model_validate(record)


@router.get("/foods/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FoodResponse:
    record = await svc.get_food_by_id(session, current_user, food_id)
    return FoodResponse.model_validate(record)


@router.post("/foods", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def create_food(
    payload: FoodCreate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FoodResponse:
    record = await svc.create_custom_food(
        session, current_user, payload.model_dump(exclude_unset=True)
    )
    await session.commit()
    return FoodResponse.model_validate(record)


@router.patch("/foods/{food_id}", response_model=FoodResponse)
async def update_food(
    food_id: UUID,
    payload: FoodUpdate,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> FoodResponse:
    record = await svc.update_custom_food(
        session, current_user, food_id, payload.model_dump(exclude_unset=True)
    )
    await session.commit()
    return FoodResponse.model_validate(record)


@router.delete("/foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(
    food_id: UUID,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await svc.delete_or_archive_custom_food(session, current_user, food_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
