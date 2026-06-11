"""Meal photo recognition pipeline.

Pure-by-default with two side-effects:
1. Calls Ollama vision model.
2. Reads `foods` table for trigram suggestions per detected food name.

Output schema is strictly validated. Malformed responses degrade to an empty
`candidates` list while preserving any raw caption Ollama returned.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import ollama
from app.clients.ollama import OllamaError
from app.config import get_settings
from app.models.food import Food
from app.models.user import User

logger = logging.getLogger(__name__)

SUGGESTIONS_PER_CANDIDATE = 3
SIMILARITY_THRESHOLD = 0.1  # lower than search; LLM names are imprecise


SYSTEM_PROMPT = (
    "You are a meal photo recognition assistant. Respond with strict JSON "
    "matching this schema: "
    '{"caption": str, "items": [{"name": str, "grams_estimate": number, '
    '"confidence": number between 0 and 1}]}. '
    "Use plain ASCII. No commentary outside the JSON. "
    "If you cannot identify any foods, return items: [] with a useful caption."
)
USER_PROMPT = (
    "Look at this meal photo. List the foods you can identify with a per-item "
    "weight estimate in grams and a confidence score between 0 and 1. Always "
    "include a one-sentence caption of the scene."
)


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class _LLMItem(BaseModel):
    """Strict validator for one item in the LLM JSON."""

    name: str = Field(min_length=1, max_length=120)
    grams_estimate: float = Field(ge=0, le=5000)
    confidence: float = Field(ge=0, le=1)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()


class _LLMResponse(BaseModel):
    caption: str = Field(default="", max_length=500)
    items: list[_LLMItem] = Field(default_factory=list)


@dataclass(frozen=True)
class Suggestion:
    food_id: UUID
    name: str
    source: str


@dataclass(frozen=True)
class Candidate:
    name: str
    grams_estimate: Decimal
    confidence: Decimal
    food_id_suggestions: list[Suggestion]


@dataclass(frozen=True)
class RecognitionResult:
    candidates: list[Candidate]
    raw_caption: str


# ---------------------------------------------------------------------------
# LLM call + parse
# ---------------------------------------------------------------------------


def _parse_llm_output(raw: str) -> _LLMResponse:
    """Parse the LLM's JSON. Tolerates trailing whitespace and a code-fence
    wrapper. On any structural problem returns an empty response.
    """
    text = raw.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences if the model adds them.
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -len("```")]
        text = text.strip()
    try:
        data = json.loads(text)
        return _LLMResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("meal_recognition_parse_failed", extra={"error": repr(exc)[:200]})
        # Best-effort: try to surface any caption embedded in malformed JSON.
        if isinstance(text, str) and '"caption"' in text:
            try:
                # naive single-key extraction
                start = text.index('"caption"')
                colon = text.index(":", start)
                snippet = text[colon + 1 :].strip()
                if snippet.startswith('"'):
                    end = snippet.index('"', 1)
                    caption = snippet[1:end]
                    return _LLMResponse(caption=caption[:500], items=[])
            except (ValueError, IndexError):
                pass
        return _LLMResponse(caption="", items=[])


# ---------------------------------------------------------------------------
# Trigram suggestions
# ---------------------------------------------------------------------------


async def _suggest_food_ids_for_name(
    session: AsyncSession, *, name: str, user: User
) -> list[Suggestion]:
    """Top N foods by trigram similarity vs `name`, scoped to public + own."""
    similarity = func.similarity(Food.name, name)
    stmt = (
        select(Food, similarity.label("similarity"))
        .where(
            Food.archived_at.is_(None),
            similarity >= SIMILARITY_THRESHOLD,
            or_(Food.owner_id.is_(None), Food.owner_id == user.id),
        )
        .order_by(similarity.desc(), Food.created_at.desc())
        .limit(SUGGESTIONS_PER_CANDIDATE)
    )
    rows = (await session.execute(stmt)).all()
    return [
        Suggestion(food_id=food.id, name=food.name, source=str(food.source.value))
        for food, _ in rows
    ]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def recognize_meal_photo(
    session: AsyncSession, *, user: User, image_bytes: bytes
) -> RecognitionResult:
    """Run the LLM, parse, build trigram suggestions. Never raises on
    upstream Ollama failure - returns empty candidates with a synthetic
    fallback caption instead.
    """
    settings = get_settings()
    try:
        raw = await ollama.generate_vision(
            prompt=USER_PROMPT,
            images=[image_bytes],
            system=SYSTEM_PROMPT,
            model=settings.ollama_vision_model,
        )
    except OllamaError as exc:
        logger.warning("meal_recognition_ollama_failed", extra={"error": repr(exc)[:200]})
        return RecognitionResult(
            candidates=[],
            raw_caption="Could not analyze the photo. Please log this meal manually.",
        )

    parsed = _parse_llm_output(raw)

    candidates: list[Candidate] = []
    for item in parsed.items:
        suggestions = await _suggest_food_ids_for_name(session, name=item.name, user=user)
        candidates.append(
            Candidate(
                name=item.name,
                grams_estimate=Decimal(str(item.grams_estimate)).quantize(Decimal("0.1")),
                confidence=Decimal(str(item.confidence)).quantize(Decimal("0.01")),
                food_id_suggestions=suggestions,
            )
        )

    caption = parsed.caption.strip()
    if not caption:
        caption = (
            f"Detected {len(candidates)} food item{'s' if len(candidates) != 1 else ''}."
            if candidates
            else "Could not identify any foods in this photo."
        )
    return RecognitionResult(candidates=candidates, raw_caption=caption)
