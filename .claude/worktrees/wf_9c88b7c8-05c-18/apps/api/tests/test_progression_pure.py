"""Pure-function tests for linear and double progression strategies."""

from __future__ import annotations

from decimal import Decimal

from app.services.progression import (
    DoubleInput,
    LinearInput,
    ProgressionSet,
    double_progression,
    linear_progression,
)


def _set(weight: str, reps: int, *, working: bool = True) -> ProgressionSet:
    return ProgressionSet(weight_kg=Decimal(weight), reps=reps, is_working=working)


# ---------------------------------------------------------------------------
# Linear progression
# ---------------------------------------------------------------------------


def test_linear_success_advances_by_increment() -> None:
    decision = linear_progression(
        LinearInput(
            last_session_sets=[_set("60", 5), _set("60", 5), _set("60", 5)],
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("62.5")
    assert decision.is_deload is False
    assert decision.consecutive_successes == 1
    assert decision.consecutive_failures == 0
    assert decision.rationale_key == "linear.advance"


def test_linear_single_fail_repeats_weight() -> None:
    decision = linear_progression(
        LinearInput(
            last_session_sets=[_set("60", 5), _set("60", 4), _set("60", 3)],
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("60")
    assert decision.is_deload is False
    assert decision.consecutive_failures == 1
    assert decision.rationale_key == "linear.repeat"


def test_linear_two_consecutive_failures_deload_10pct() -> None:
    decision = linear_progression(
        LinearInput(
            last_session_sets=[_set("100", 4), _set("100", 4), _set("100", 4)],
            target_reps=5,
            increment_kg=Decimal("5"),
            current_weight_kg=Decimal("100"),
            consecutive_failures=1,
        )
    )
    # 100 * 0.9 = 90 -> rounded to nearest 0.5 -> 90.00
    assert decision.next_weight_kg == Decimal("90.00")
    assert decision.is_deload is True
    assert decision.consecutive_failures == 0
    assert decision.rationale_key == "linear.deload"


def test_linear_no_working_sets_holds() -> None:
    decision = linear_progression(
        LinearInput(
            last_session_sets=[_set("50", 5, working=False)],
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("50"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("50")
    assert decision.is_deload is False
    assert decision.rationale_key == "linear.hold.no_data"


def test_linear_ignores_warmups_for_success_check() -> None:
    decision = linear_progression(
        LinearInput(
            last_session_sets=[
                _set("40", 3, working=False),  # warmup that "fails"
                _set("60", 5),
                _set("60", 5),
            ],
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("62.5")
    assert decision.consecutive_successes == 1


# ---------------------------------------------------------------------------
# Double progression
# ---------------------------------------------------------------------------


def test_double_all_top_advances_and_resets_reps() -> None:
    decision = double_progression(
        DoubleInput(
            last_session_sets=[_set("60", 12), _set("60", 12), _set("60", 12)],
            target_reps_low=8,
            target_reps_high=12,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("62.5")
    assert decision.next_reps_low == 8
    assert decision.next_reps_high == 12
    assert decision.rationale_key == "double.advance_weight"
    assert decision.is_deload is False


def test_double_within_range_adds_rep_to_lowest() -> None:
    decision = double_progression(
        DoubleInput(
            last_session_sets=[_set("60", 12), _set("60", 10), _set("60", 9)],
            target_reps_low=8,
            target_reps_high=12,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("60")
    assert decision.next_reps_low == 10  # lowest (9) + 1
    assert decision.next_reps_high == 12
    assert decision.rationale_key == "double.add_rep"


def test_double_below_low_is_failure() -> None:
    decision = double_progression(
        DoubleInput(
            last_session_sets=[_set("60", 8), _set("60", 7), _set("60", 6)],
            target_reps_low=8,
            target_reps_high=12,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    assert decision.next_weight_kg == Decimal("60")
    assert decision.is_deload is False
    assert decision.consecutive_failures == 1
    assert decision.rationale_key == "double.repeat"


def test_double_two_consecutive_failures_deload_5pct() -> None:
    decision = double_progression(
        DoubleInput(
            last_session_sets=[_set("100", 6), _set("100", 5), _set("100", 5)],
            target_reps_low=8,
            target_reps_high=12,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("100"),
            consecutive_failures=1,
        )
    )
    # 100 * 0.95 = 95.00
    assert decision.next_weight_kg == Decimal("95.00")
    assert decision.is_deload is True
    assert decision.consecutive_failures == 0
    assert decision.rationale_key == "double.deload"


def test_double_lowest_rep_does_not_exceed_high() -> None:
    """If lowest rep is already at high, adding one would exceed high. Cap at high."""
    decision = double_progression(
        DoubleInput(
            last_session_sets=[_set("60", 12), _set("60", 11), _set("60", 11)],
            target_reps_low=8,
            target_reps_high=12,
            increment_kg=Decimal("2.5"),
            current_weight_kg=Decimal("60"),
            consecutive_failures=0,
        )
    )
    # Lowest 11 -> add 1 -> 12 (capped at high).
    assert decision.next_reps_low == 12
    assert decision.next_weight_kg == Decimal("60")


# ---------------------------------------------------------------------------
# 4-session hand-checked sequence (acceptance criterion)
# ---------------------------------------------------------------------------


def test_4_session_linear_sequence_matches_expected() -> None:
    """Mock 4 sessions on bench press starting at 60 kg target 5 reps.
    Sessions: succeed, succeed, fail, fail -> expect 60, 62.5, 65, 65, 58.5"""
    weight = Decimal("60")
    failures = 0
    history = [weight]

    # Session 1: hit all 3x5 at 60.
    d = linear_progression(
        LinearInput(
            last_session_sets=[_set(str(weight), 5)] * 3,
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=weight,
            consecutive_failures=failures,
        )
    )
    weight, failures = d.next_weight_kg, d.consecutive_failures
    history.append(weight)
    assert weight == Decimal("62.5")

    # Session 2: hit 3x5 at 62.5.
    d = linear_progression(
        LinearInput(
            last_session_sets=[_set(str(weight), 5)] * 3,
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=weight,
            consecutive_failures=failures,
        )
    )
    weight, failures = d.next_weight_kg, d.consecutive_failures
    history.append(weight)
    assert weight == Decimal("65.0")

    # Session 3: miss on last set (5/5/4 at 65).
    d = linear_progression(
        LinearInput(
            last_session_sets=[_set(str(weight), 5), _set(str(weight), 5), _set(str(weight), 4)],
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=weight,
            consecutive_failures=failures,
        )
    )
    weight, failures = d.next_weight_kg, d.consecutive_failures
    history.append(weight)
    assert weight == Decimal("65")  # repeat
    assert failures == 1

    # Session 4: miss again -> deload 10% = 58.5.
    d = linear_progression(
        LinearInput(
            last_session_sets=[_set(str(weight), 5), _set(str(weight), 5), _set(str(weight), 4)],
            target_reps=5,
            increment_kg=Decimal("2.5"),
            current_weight_kg=weight,
            consecutive_failures=failures,
        )
    )
    weight, failures = d.next_weight_kg, d.consecutive_failures
    history.append(weight)
    # 65 * 0.9 = 58.5
    assert weight == Decimal("58.5")
    assert d.is_deload is True
    assert failures == 0
