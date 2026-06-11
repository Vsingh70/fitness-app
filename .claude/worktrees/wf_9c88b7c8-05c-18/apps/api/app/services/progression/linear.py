"""Linear progression.

Spec:
- Success at the prescribed reps on every working set -> add the increment.
- 1 failed session -> repeat the weight.
- 2 consecutive failures -> deload 10%.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.progression._types import LinearInput, ProgressionDecision

DELOAD_FACTOR = Decimal("0.9")
QUANT = Decimal("0.5")


def _quantize_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    """Round value to the nearest multiple of `increment` (default 0.5 kg)."""
    step = increment if increment <= Decimal("1") else QUANT
    quantized = (value / step).quantize(Decimal("1")) * step
    return quantized.quantize(Decimal("0.01"))


def linear_progression(input: LinearInput) -> ProgressionDecision:
    working = [s for s in input.last_session_sets if s.is_working]
    if not working:
        # No working sets logged -> hold weight, no failure counted.
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg,
            next_reps_low=input.target_reps,
            next_reps_high=input.target_reps,
            is_deload=False,
            rationale_key="linear.hold.no_data",
            consecutive_failures=input.consecutive_failures,
            consecutive_successes=0,
        )

    success = all((s.reps or 0) >= input.target_reps for s in working)

    if success:
        next_weight = input.current_weight_kg + input.increment_kg
        return ProgressionDecision(
            next_weight_kg=next_weight,
            next_reps_low=input.target_reps,
            next_reps_high=input.target_reps,
            is_deload=False,
            rationale_key="linear.advance",
            consecutive_failures=0,
            consecutive_successes=1,
        )

    failures = input.consecutive_failures + 1
    if failures >= 2:
        deloaded = _quantize_to_increment(
            input.current_weight_kg * DELOAD_FACTOR, input.increment_kg
        )
        return ProgressionDecision(
            next_weight_kg=deloaded,
            next_reps_low=input.target_reps,
            next_reps_high=input.target_reps,
            is_deload=True,
            rationale_key="linear.deload",
            consecutive_failures=0,
            consecutive_successes=0,
        )

    return ProgressionDecision(
        next_weight_kg=input.current_weight_kg,
        next_reps_low=input.target_reps,
        next_reps_high=input.target_reps,
        is_deload=False,
        rationale_key="linear.repeat",
        consecutive_failures=failures,
        consecutive_successes=0,
    )
