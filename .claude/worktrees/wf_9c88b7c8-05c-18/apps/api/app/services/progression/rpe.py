"""RPE-based progression.

Rule table (documented per the acceptance criterion):

    avg_top_set_rpe < target_low                                -> increase weight by 1 step (default 2.5%)
    target_low <= rpe <= target_high AND any set < reps_high    -> hold weight, add 1 rep to lowest set
    target_low <= rpe <= target_high AND all sets >= reps_high  -> increase weight by 1 step
    target_high < rpe <= target_high + 1.0                      -> hold weight, push reps next time
    rpe > target_high + 1.0                                     -> back off 5% next session
    consecutive_above >= 3                                      -> deload 5% AND reset consecutive_above

Top-set selection: all working sets at the heaviest weight performed.
Effective per-set RPE: `rpe if rpe is not None else (10 - rir)` when RIR is present.

The e1RM sanity cap: if the next-session recommendation implies a top-set e1RM
more than 2.5% above the median of `recent_e1rm`, the new weight is reduced so
the implied e1RM lands exactly at that cap. Skipped silently when fewer than 2
historical e1RMs are available.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.progression._types import (
    ProgressionDecision,
    ProgressionSet,
    RPEInput,
)

BACK_OFF_FACTOR = Decimal("0.95")
DELOAD_FACTOR = Decimal("0.95")
E1RM_CAP_PCT = Decimal("0.025")
QUANT = Decimal("0.5")


def _quantize(value: Decimal) -> Decimal:
    return ((value / QUANT).quantize(Decimal("1")) * QUANT).quantize(Decimal("0.01"))


def _effective_rpe(rpe: Decimal | None, rir: int | None) -> Decimal | None:
    if rpe is not None:
        return rpe
    if rir is not None:
        return Decimal(10) - Decimal(rir)
    return None


def _top_set_local_indexes(working: list[ProgressionSet]) -> list[int]:
    weights = [s.weight_kg for s in working if s.weight_kg is not None]
    if not weights:
        return []
    top = max(weights)
    return [i for i, s in enumerate(working) if s.weight_kg == top]


def _average_top_rpe(input: RPEInput) -> Decimal | None:
    working_pairs: list[tuple[int, ProgressionSet]] = [
        (i, s) for i, s in enumerate(input.last_session_sets) if s.is_working
    ]
    if not working_pairs:
        return None
    working = [s for _, s in working_pairs]
    top_local = _top_set_local_indexes(working)
    if not top_local:
        return None
    original_indexes = [working_pairs[i][0] for i in top_local]
    effective: list[Decimal] = []
    for orig_i in original_indexes:
        ev = _effective_rpe(input.set_rpes[orig_i], input.set_rirs[orig_i])
        if ev is not None:
            effective.append(ev)
    if not effective:
        return None
    return sum(effective, Decimal(0)) / Decimal(len(effective))


def epley_e1rm(weight: Decimal, reps: int) -> Decimal:
    if reps <= 0:
        return Decimal(0)
    return (weight * (Decimal(1) + Decimal(reps) / Decimal(30))).quantize(Decimal("0.01"))


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return ((sorted_values[mid - 1] + sorted_values[mid]) / Decimal(2)).quantize(Decimal("0.01"))


def _apply_e1rm_cap(
    proposed_weight: Decimal,
    proposed_reps_low: int,
    recent_e1rm: list[Decimal],
) -> Decimal:
    if len(recent_e1rm) < 2:
        return proposed_weight
    median = _median(recent_e1rm)
    if median is None or median <= 0:
        return proposed_weight
    implied = epley_e1rm(proposed_weight, proposed_reps_low)
    cap = (median * (Decimal(1) + E1RM_CAP_PCT)).quantize(Decimal("0.01"))
    if implied <= cap:
        return proposed_weight
    # weight = cap / (1 + reps/30)
    factor = Decimal(1) + Decimal(proposed_reps_low) / Decimal(30)
    return _quantize((cap / factor).quantize(Decimal("0.01")))


def rpe_progression(input: RPEInput) -> ProgressionDecision:
    working = [s for s in input.last_session_sets if s.is_working]
    if not working:
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="rpe.hold.no_data",
            consecutive_failures=0,
            consecutive_successes=0,
            consecutive_above=input.consecutive_above,
        )

    avg_rpe = _average_top_rpe(input)
    if avg_rpe is None:
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="rpe.hold.no_rpe",
            consecutive_failures=0,
            consecutive_successes=0,
            consecutive_above=input.consecutive_above,
        )

    step = (input.current_weight_kg * input.increment_pct).quantize(Decimal("0.01"))
    above_by = avg_rpe - input.target_rpe_high

    if above_by > 0:
        new_consec_above = input.consecutive_above + 1
        if new_consec_above >= 3:
            return ProgressionDecision(
                next_weight_kg=_quantize(input.current_weight_kg * DELOAD_FACTOR),
                next_reps_low=input.target_reps_low,
                next_reps_high=input.target_reps_high,
                is_deload=True,
                rationale_key="rpe.deload.consecutive_above",
                consecutive_failures=0,
                consecutive_successes=0,
                consecutive_above=0,
            )
        if above_by > Decimal("1.0"):
            return ProgressionDecision(
                next_weight_kg=_quantize(input.current_weight_kg * BACK_OFF_FACTOR),
                next_reps_low=input.target_reps_low,
                next_reps_high=input.target_reps_high,
                is_deload=False,
                rationale_key="rpe.back_off.far_above",
                consecutive_failures=0,
                consecutive_successes=0,
                consecutive_above=new_consec_above,
            )
        # 0 < above_by <= 1.0  -> hold weight, push reps next time
        return ProgressionDecision(
            next_weight_kg=input.current_weight_kg,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="rpe.hold.slightly_above",
            consecutive_failures=0,
            consecutive_successes=0,
            consecutive_above=new_consec_above,
        )

    # Within or below range -> consecutive_above resets.
    if avg_rpe < input.target_rpe_low:
        proposed = _quantize(input.current_weight_kg + step)
        proposed = _apply_e1rm_cap(proposed, input.target_reps_low, input.recent_e1rm)
        return ProgressionDecision(
            next_weight_kg=proposed,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="rpe.advance.below_range",
            consecutive_failures=0,
            consecutive_successes=1,
            consecutive_above=0,
        )

    reps_high = input.target_reps_high or input.target_reps_low
    reps = [(s.reps or 0) for s in working]
    if all(r >= reps_high for r in reps):
        proposed = _quantize(input.current_weight_kg + step)
        proposed = _apply_e1rm_cap(proposed, input.target_reps_low, input.recent_e1rm)
        return ProgressionDecision(
            next_weight_kg=proposed,
            next_reps_low=input.target_reps_low,
            next_reps_high=input.target_reps_high,
            is_deload=False,
            rationale_key="rpe.advance.in_range_top",
            consecutive_failures=0,
            consecutive_successes=1,
            consecutive_above=0,
        )

    lowest = min(reps)
    next_low = min(lowest + 1, reps_high)
    return ProgressionDecision(
        next_weight_kg=input.current_weight_kg,
        next_reps_low=next_low,
        next_reps_high=input.target_reps_high,
        is_deload=False,
        rationale_key="rpe.add_rep.in_range",
        consecutive_failures=0,
        consecutive_successes=1,
        consecutive_above=0,
    )
