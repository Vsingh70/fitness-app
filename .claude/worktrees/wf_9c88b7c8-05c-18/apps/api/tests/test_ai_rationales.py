"""Pure tests for the rationale generator, fallback renderer, and validator."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.clients import ollama as ollama_module
from app.services.ai.fallbacks import render_fallback
from app.services.ai.rationales import (
    RationaleContext,
    RationaleRequest,
    _validate,
    generate_rationale,
)


def _req(**overrides: Any) -> RationaleRequest:
    base = {
        "rationale_key": "linear.advance",
        "next_weight_kg": Decimal("62.50"),
        "next_reps_low": 5,
        "next_reps_high": None,
        "is_deload": False,
        "template_variables": {"increment_kg": "2.50"},
        "context": RationaleContext(
            exercise_name="Bench Press",
            prior_weight_kg=Decimal("60.00"),
            last_three_sessions=[
                "2026-05-24: top-set 60kg x 5",
                "2026-05-21: top-set 57.5kg x 5",
            ],
        ),
    }
    base.update(overrides)
    return RationaleRequest(**base)


# Renderer ------------------------------------------------------------------


def test_render_fallback_interpolates_variables() -> None:
    out = render_fallback("linear.advance", {"increment_kg": "2.50"})
    assert out == "You hit all sets, so weight is going up by 2.50 kg next time."


def test_render_fallback_missing_var_returns_generic() -> None:
    out = render_fallback("linear.advance", {})
    assert out == "Plan updated based on your last session."


def test_render_fallback_unknown_key_returns_generic() -> None:
    out = render_fallback("not.a.real.key", {})
    assert out == "Plan updated based on your last session."


def test_render_fallback_no_key_returns_generic() -> None:
    assert render_fallback(None) == "Plan updated based on your last session."


def test_render_fallback_no_vars_needed() -> None:
    """rpe.advance.below_range has no {var}, so an empty dict still works."""
    out = render_fallback("rpe.advance.below_range")
    assert "RPE was below your target range" in out


# Validator -----------------------------------------------------------------


def test_validate_accepts_clean_one_sentence() -> None:
    assert _validate("You hit all sets, so weight is going up by 2.5 kg next time.")


def test_validate_rejects_em_dash() -> None:
    assert not _validate("You hit all sets — weight is going up.")


def test_validate_rejects_en_dash() -> None:
    assert not _validate("You hit all sets – weight is going up.")


def test_validate_rejects_exclamation() -> None:
    assert not _validate("You hit all sets!")


def test_validate_rejects_emoji() -> None:
    assert not _validate("You hit all sets, weight is going up 💪.")


def test_validate_rejects_too_long() -> None:
    assert not _validate("a" * 201)


def test_validate_rejects_multiline() -> None:
    assert not _validate("First line.\nSecond line.")


def test_validate_rejects_empty() -> None:
    assert not _validate("")


# generate_rationale --------------------------------------------------------


async def test_generate_rationale_uses_clean_llm_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate(**kwargs: Any) -> str:
        return "You hit all sets at this weight, so weight is moving up next session."

    monkeypatch.setattr(ollama_module, "generate", fake_generate)
    out = await generate_rationale(_req())
    assert out == "You hit all sets at this weight, so weight is moving up next session."


async def test_generate_rationale_strips_quotes_and_bullets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate(**kwargs: Any) -> str:
        return '"- You hit all sets, so weight goes up next time."'

    monkeypatch.setattr(ollama_module, "generate", fake_generate)
    out = await generate_rationale(_req())
    assert out == "You hit all sets, so weight goes up next time."


async def test_generate_rationale_falls_back_on_bad_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Output containing an em dash must be rejected, fallback used."""

    async def fake_generate(**kwargs: Any) -> str:
        return "You hit all sets — weight is going up."

    monkeypatch.setattr(ollama_module, "generate", fake_generate)
    out = await generate_rationale(_req())
    assert out == "You hit all sets, so weight is going up by 2.50 kg next time."


async def test_generate_rationale_falls_back_on_ollama_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate(**kwargs: Any) -> str:
        raise ollama_module.OllamaError("connection refused")

    monkeypatch.setattr(ollama_module, "generate", fake_generate)
    out = await generate_rationale(_req())
    assert out == "You hit all sets, so weight is going up by 2.50 kg next time."


async def test_generate_rationale_unknown_key_uses_generic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate(**kwargs: Any) -> str:
        raise ollama_module.OllamaError("down")

    monkeypatch.setattr(ollama_module, "generate", fake_generate)
    out = await generate_rationale(_req(rationale_key="unknown.key", template_variables={}))
    assert out == "Plan updated based on your last session."
