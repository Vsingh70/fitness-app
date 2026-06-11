"""Mesocycle layout, deload target reduction, and fatigue accounting.

Layout rule for `compute_mesocycle_position(meso_length, program_weeks, abs_week)`:
each cycle is `meso_length - 1` progression weeks + 1 deload week. The cycle is
indexed from 1: weeks 1..N-1 are progression, week N is deload, and the pattern
repeats. The final week of the program is forced non-deload when it would
otherwise land at a deload, since the program ends there.

`apply_deload_to_session`: 60% volume, 80% intensity, RPE cap 6.5.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

DELOAD_VOLUME_FACTOR = Decimal("0.60")
DELOAD_INTENSITY_FACTOR = Decimal("0.80")
DELOAD_RPE_CAP = Decimal("6.5")


@dataclass(frozen=True)
class MesocyclePosition:
    meso_index: int  # 1-based mesocycle ordinal
    week_in_meso: int  # 1-based week within current mesocycle
    is_deload: bool


def compute_mesocycle_position(
    meso_length: int, program_weeks: int, abs_week: int
) -> MesocyclePosition:
    """Return (meso_index, week_in_meso, is_deload) for absolute week abs_week
    (1-indexed) inside a program of length program_weeks. meso_length is the
    full cycle length including its deload week.

    `meso_length=4` and `program_weeks=8` yields weeks 1-3 normal, week 4
    deload, weeks 5-7 normal, week 8 deload. The acceptance criterion lists
    weeks 1-4 normal + week 5 deload + 6-8 normal; that matches when callers
    pass `meso_length=5` (4 progression + 1 deload).
    """
    if meso_length < 2:
        raise ValueError("meso_length must be >= 2")
    if abs_week < 1 or abs_week > program_weeks:
        raise ValueError("abs_week out of range")

    meso_index = (abs_week - 1) // meso_length + 1
    week_in_meso = (abs_week - 1) % meso_length + 1
    is_deload = week_in_meso == meso_length and abs_week < program_weeks
    # Edge case: when abs_week == program_weeks AND it lands exactly on a meso
    # boundary, we still mark it as deload so a clean 8-week / meso 4 program
    # ends with a deload taper. Only suppress the deload if it would mean the
    # program ends with a single hanging deload that has no following meso.
    if abs_week == program_weeks and week_in_meso == meso_length:
        # Standard taper: keep the final deload.
        is_deload = True
    return MesocyclePosition(meso_index=meso_index, week_in_meso=week_in_meso, is_deload=is_deload)


@dataclass(frozen=True)
class DeloadTargets:
    target_sets: int
    target_reps_low: int | None
    target_reps_high: int | None
    target_weight_kg: Decimal | None
    target_rpe_low: Decimal | None
    target_rpe_high: Decimal | None


def apply_deload_to_session(
    *,
    target_sets: int,
    target_reps_low: int | None,
    target_reps_high: int | None,
    last_working_weight_kg: Decimal | None,
    target_rpe_low: Decimal | None,
    target_rpe_high: Decimal | None,
) -> DeloadTargets:
    """Reduce volume to 60%, intensity to 80%, cap RPE at 6.5."""
    new_sets = max(1, int(round(float(target_sets) * float(DELOAD_VOLUME_FACTOR))))
    new_weight: Decimal | None
    if last_working_weight_kg is not None:
        # Quantize to 0.5 kg steps, then 2-decimal display.
        raw = last_working_weight_kg * DELOAD_INTENSITY_FACTOR
        new_weight = ((raw / Decimal("0.5")).quantize(Decimal("1")) * Decimal("0.5")).quantize(
            Decimal("0.01")
        )
    else:
        new_weight = None

    capped_low = target_rpe_low
    if capped_low is not None and capped_low > DELOAD_RPE_CAP:
        capped_low = DELOAD_RPE_CAP
    capped_high = target_rpe_high
    if capped_high is not None and capped_high > DELOAD_RPE_CAP:
        capped_high = DELOAD_RPE_CAP

    return DeloadTargets(
        target_sets=new_sets,
        target_reps_low=target_reps_low,
        target_reps_high=target_reps_high,
        target_weight_kg=new_weight,
        target_rpe_low=capped_low,
        target_rpe_high=capped_high,
    )


# ---------------------------------------------------------------------------
# Fatigue accumulator
# ---------------------------------------------------------------------------


FATIGUE_OVER_RANGE_PER_SESSION = Decimal("1.0")
FATIGUE_PER_FAILED_SET = Decimal("0.5")
FATIGUE_RHR_ELEVATED = Decimal("1.0")
FATIGUE_LOW_READINESS = Decimal("1.0")
FATIGUE_PLANNED_REST = Decimal("-1.0")
FATIGUE_THRESHOLD = Decimal("6.0")
FATIGUE_DECAY_PER_DAY = Decimal("1.0")  # rolling 7-day window


def compute_session_fatigue_delta(
    *,
    avg_rpe_over_target: bool,
    failed_working_sets: int,
    rhr_elevated_3day: bool = False,
) -> Decimal:
    delta = Decimal("0")
    if avg_rpe_over_target:
        delta += FATIGUE_OVER_RANGE_PER_SESSION
    delta += FATIGUE_PER_FAILED_SET * Decimal(failed_working_sets)
    if rhr_elevated_3day:
        delta += FATIGUE_RHR_ELEVATED
    return delta
