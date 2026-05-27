from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProgressionSet:
    """The subset of a logged set the progression strategies care about."""

    weight_kg: Decimal | None
    reps: int | None
    is_working: bool = True


@dataclass(frozen=True)
class LinearInput:
    """Inputs for linear progression on a single exercise.

    `target_reps` is a single rep target (e.g. 5 for Starting Strength). A set
    is a success if `reps >= target_reps`. All working sets must succeed.
    """

    last_session_sets: list[ProgressionSet]
    target_reps: int
    increment_kg: Decimal
    current_weight_kg: Decimal
    consecutive_failures: int


@dataclass(frozen=True)
class DoubleInput:
    """Inputs for double progression.

    Success per set = `reps >= target_reps_high`. Failure = any set below
    `target_reps_low`. Otherwise: hold weight, target one more rep on the
    lowest-rep set.
    """

    last_session_sets: list[ProgressionSet]
    target_reps_low: int
    target_reps_high: int
    increment_kg: Decimal
    current_weight_kg: Decimal
    consecutive_failures: int


@dataclass(frozen=True)
class RPEInput:
    """Inputs for RPE-based progression.

    Top-set RPE is averaged across all working sets at the heaviest weight
    performed. Per-set RPE falls back to RIR via `10 - rir` when RPE is missing.
    `recent_e1rm` is the chronological list of estimated 1RMs from prior
    sessions of this exercise; the sanity cap uses its median.
    """

    last_session_sets: list[ProgressionSet]
    set_rpes: list[Decimal | None]
    set_rirs: list[int | None]
    target_rpe_low: Decimal
    target_rpe_high: Decimal
    target_reps_low: int
    target_reps_high: int | None
    increment_pct: Decimal
    current_weight_kg: Decimal
    consecutive_above: int
    recent_e1rm: list[Decimal]


@dataclass(frozen=True)
class ProgressionDecision:
    next_weight_kg: Decimal
    next_reps_low: int
    next_reps_high: int | None
    is_deload: bool
    rationale_key: str
    # Updated rolling state to persist back to exercise_progression.
    consecutive_failures: int
    consecutive_successes: int
    # Used by RPE-based progression; linear/double leave at 0.
    consecutive_above: int = 0

    @property
    def kind(self) -> str:
        """Maps to the recommendation_kind enum value."""
        if self.is_deload:
            return "deload"
        # next_weight > 0 and increased relative to caller's prior weight is
        # determined by the caller; we expose a coarse 'kind' from the decision
        # alone: deload, hold, or increase. The caller maps to increase_reps
        # vs. increase_weight when relevant.
        return "increase_weight"
