from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.meal_photo import FoodSuggestion, MealCandidate, MealRecognizeResponse
from app.services.ai import photo_recognition
from app.services.rate_limit import (
    PHOTO_RECOGNIZE_HOURLY_LIMIT,
    acquire_photo_slot,
    check_hourly_limit,
)
from app.services.storage import meal_photos

router = APIRouter(tags=["meals"])


@router.post("/meals/recognize", response_model=MealRecognizeResponse)
async def recognize_meal_photo(
    photo: UploadFile = File(...),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> MealRecognizeResponse:
    await check_hourly_limit(
        current_user.id,
        key_namespace="photo_recognize",
        limit=PHOTO_RECOGNIZE_HOURLY_LIMIT,
    )
    async with acquire_photo_slot():
        raw_bytes = await photo.read()
        stored = meal_photos.save_meal_photo(
            user_id=current_user.id,
            raw_bytes=raw_bytes,
            content_type=photo.content_type,
        )
        # Re-read the processed JPEG so the model gets the stripped/resized
        # bytes, which is what we keep on disk anyway.
        processed_bytes = stored.absolute_path.read_bytes()
        result = await photo_recognition.recognize_meal_photo(
            session, user=current_user, image_bytes=processed_bytes
        )
        photo_url = meal_photos.sign_url(stored.relative_path)
    return MealRecognizeResponse(
        candidates=[
            MealCandidate(
                name=c.name,
                grams_estimate=c.grams_estimate,
                confidence=c.confidence,
                food_id_suggestions=[
                    FoodSuggestion(food_id=s.food_id, name=s.name, source=s.source)
                    for s in c.food_id_suggestions
                ],
            )
            for c in result.candidates
        ],
        raw_caption=result.raw_caption,
        photo_url=photo_url,
    )
