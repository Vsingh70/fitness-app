"""Double progression.

Spec:
- Target a rep range like 8 to 12.
- If all working sets hit the top of the range, increase weight by the
  increment and reset reps to the bottom of the range.
- Otherwise, try to add one rep to the lowest-rep set next time.
- Failure = reps below the bottom of the range on any working set.
- After 2 consecutive failures, deload 5%.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.progression._types import DoubleInput, ProgressionDecision

DELOAD_FACTOR = Decimal("0.95")
QUANT = Decimal("0.5")


def _quantize_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    step = increment if increment <= Decimal("1") else QUANT
    quantized = (value / step).quantize(Decimal("1")) * step
    return quantized.quantize(Decimal("0.01"))


def double_progression(input: DoubleInput) -> ProgressionDecision:
    working = [s for s in input.last_session_sets if s.is_working]
    if not working:
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="double.hold.no_data",
            consecutive_failures=input.consecutive_failures,
            consecutive_successes=0,
        )

    reps = [(s.reps or 0) for s in working]
    if any(r < input.target_reps_low for r in reps):
        failures = input.consecutive_failures + 1
        if failures >= 2:
            deloaded = _quantize_to_increment(
                input.current_weight_kg * DELOAD_FACTOR, input.increment_kg
            )
            return ProgressionDecision(
                next_weight_kg=deloaded,
                next_reps_low=input.target_reps_low,
                next_reps_high=input.target_reps_high,
                is_deload=True,
                rationale_key="double.deload",
                consecutive_failures=0,
                consecutive_successes=0,
            )
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="double.repeat",
            consecutive_failures=failures,
            consecutive_successes=0,
        )

    if all(r >= input.target_reps_high for r in reps):
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg + input.increment_kg,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="double.advance_weight",
            consecutive_failures=0,
            consecutive_successes=1,
        )

    # Within the range -> hold weight, push reps up.
    lowest = min(reps)
    next_target = min(lowest + 1, input.target_reps_high)
    return ProgressionDecision(
        next_weight_kg=input.current_weight_kg,
        next_reps_low=next_target,
        next_reps_high=input.target_reps_high,
        is_deload=False,
        rationale_key="double.add_rep",
        consecutive_failures=0,
        consecutive_successes=1,
    )
