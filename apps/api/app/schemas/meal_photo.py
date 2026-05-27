from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class FoodSuggestion(BaseModel):
    food_id: UUID
    name: str
    source: str


class MealCandidate(BaseModel):
    name: str
    grams_estimate: Decimal
    confidence: Decimal
    food_id_suggestions: list[FoodSuggestion]


class MealRecognizeResponse(BaseModel):
    candidates: list[MealCandidate]
    raw_caption: str
    photo_url: str | None = None
