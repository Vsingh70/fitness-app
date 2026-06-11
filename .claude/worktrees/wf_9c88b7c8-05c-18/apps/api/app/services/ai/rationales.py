"""Generate a one-sentence rationale for a ProgressionDecision via Ollama,
falling back to a templated string from fallbacks.yaml on any failure.

Style constraints enforced by both prompt and post-validation:
- One sentence
- Max 200 chars
- No em dash, en dash, emoji, or exclamation mark
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.clients import ollama
from app.clients.ollama import OllamaError
from app.services.ai.fallbacks import render_fallback

MAX_LEN = 200
BANNED_CHARS = {"—", "–"}  # em dash, en dash
BANNED_SUBSTRINGS = {"!"}
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f9ff"  # symbols & pictographs, emoticons, etc.
    "\U0001fa00-\U0001faff"
    "\U00002600-\U000026ff"
    "\U00002700-\U000027bf"
    "]",
    flags=re.UNICODE,
)


@dataclass(frozen=True)
class RationaleContext:
    exercise_name: str
    prior_weight_kg: Decimal | None
    last_three_sessions: list[str]  # short human-readable summaries, newest first


@dataclass(frozen=True)
class RationaleRequest:
    rationale_key: str
    next_weight_kg: Decimal | None
    next_reps_low: int | None
    next_reps_high: int | None
    is_deload: bool
    template_variables: dict[str, str]
    context: RationaleContext


SYSTEM_PROMPT = (
    "You write one short sentence explaining a strength-training progression decision "
    "to a lifter. Style rules: exactly one sentence; under 200 characters; plain ASCII; "
    "no em dash, no en dash, no emoji, no exclamation marks; direct and friendly. "
    "Examples:\n"
    "- You hit all sets, so weight is going up by 2.5 kg next time.\n"
    "- RPE was below your target range, so weight goes up by 2.5 percent.\n"
    "- Two misses in a row, so weight drops 10 percent next session for a reset.\n"
    "Match this style."
)


def _build_user_prompt(req: RationaleRequest) -> str:
    lines = [
        f"Exercise: {req.context.exercise_name}",
        f"Rationale key: {req.rationale_key}",
    ]
    if req.context.prior_weight_kg is not None:
        lines.append(f"Prior top-set weight: {req.context.prior_weight_kg} kg")
    if req.next_weight_kg is not None:
        lines.append(f"Next weight: {req.next_weight_kg} kg")
    if req.next_reps_low is not None:
        rng = (
            f"{req.next_reps_low}-{req.next_reps_high}"
            if req.next_reps_high and req.next_reps_high != req.next_reps_low
            else str(req.next_reps_low)
        )
        lines.append(f"Next reps: {rng}")
    if req.is_deload:
        lines.append("This is a deload recommendation.")
    if req.context.last_three_sessions:
        lines.append("Last sessions (newest first):")
        for s in req.context.last_three_sessions:
            lines.append(f"- {s}")
    lines.append("Write the one-sentence explanation.")
    return "\n".join(lines)


def _validate(text: str) -> bool:
    if not text:
        return False
    if len(text) > MAX_LEN:
        return False
    if any(c in text for c in BANNED_CHARS):
        return False
    if any(s in text for s in BANNED_SUBSTRINGS):
        return False
    if _EMOJI_RE.search(text):
        return False
    # Reject obvious multi-sentence outputs.
    return not (text.count(".") > 2 or "\n" in text)


def _normalize(text: str) -> str:
    """Trim quotes / list-bullet artifacts and whitespace."""
    cleaned = text.strip().strip('"').strip("'")
    # Drop a leading "- " bullet if the model returned a list-style line.
    if cleaned.startswith("- "):
        cleaned = cleaned[2:].strip()
    return cleaned


async def generate_rationale(req: RationaleRequest) -> str:
    """Return a one-sentence rationale string.

    On Ollama failure or invalid output, return the templated fallback so
    callers never get an exception. Safe to call from the ARQ task.
    """
    try:
        raw = await ollama.generate(
            prompt=_build_user_prompt(req),
            system=SYSTEM_PROMPT,
        )
    except OllamaError:
        return render_fallback(req.rationale_key, req.template_variables)

    normalized = _normalize(raw)
    if not _validate(normalized):
        return render_fallback(req.rationale_key, req.template_variables)
    return normalized
