"""Pure-function tests for mesocycle math and deload target reduction."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.progression.mesocycle import (
    apply_deload_to_session,
    compute_mesocycle_position,
    compute_session_fatigue_delta,
)


def test_8_week_program_meso_4_lays_out_correctly() -> None:
    """meso_length=4 over 8 weeks: weeks 1-3 progression, week 4 deload,
    weeks 5-7 progression, week 8 deload.
    """
    expected = [False, False, False, True, False, False, False, True]
    actual = [compute_mesocycle_position(4, 8, w).is_deload for w in range(1, 9)]
    assert actual == expected


def test_5_week_meso_over_8_week_program_matches_acceptance_criteria() -> None:
    """Acceptance criterion: with default meso length, an 8-week program has
    weeks 1-4 normal, week 5 deload, weeks 6-8 normal. With meso_length=5
    (4 progression + 1 deload) the engine produces exactly that.
    """
    expected = [False, False, False, False, True, False, False, False]
    actual = [compute_mesocycle_position(5, 8, w).is_deload for w in range(1, 9)]
    assert actual == expected


def test_week_in_meso_cycles() -> None:
    """week_in_meso resets at every meso boundary."""
    weeks = [compute_mesocycle_position(4, 12, w) for w in range(1, 13)]
    assert [p.week_in_meso for p in weeks] == [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4]
    assert [p.meso_index for p in weeks] == [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]


def test_meso_length_minimum_validated() -> None:
    with pytest.raises(ValueError):
        compute_mesocycle_position(1, 4, 1)


def test_abs_week_out_of_range() -> None:
    with pytest.raises(ValueError):
        compute_mesocycle_position(4, 4, 5)
    with pytest.raises(ValueError):
        compute_mesocycle_position(4, 4, 0)


def test_apply_deload_reduces_volume_intensity_and_caps_rpe() -> None:
    out = apply_deload_to_session(
        target_sets=5,
        target_reps_low=5,
        target_reps_high=8,
        last_working_weight_kg=Decimal("100"),
        target_rpe_low=Decimal("8"),
        target_rpe_high=Decimal("9"),
    )
    # 60% of 5 = 3.0 sets
    assert out.target_sets == 3
    # 80% of 100 = 80.00 (already plate-friendly)
    assert out.target_weight_kg == Decimal("80.00")
    # rpe capped at 6.5
    assert out.target_rpe_low == Decimal("6.5")
    assert out.target_rpe_high == Decimal("6.5")
    # reps preserved
    assert out.target_reps_low == 5
    assert out.target_reps_high == 8


def test_apply_deload_minimum_one_set() -> None:
    out = apply_deload_to_session(
        target_sets=1,
        target_reps_low=5,
        target_reps_high=None,
        last_working_weight_kg=Decimal("100"),
        target_rpe_low=None,
        target_rpe_high=None,
    )
    assert out.target_sets == 1


def test_apply_deload_quantizes_to_half_kg() -> None:
    # 80% of 102.5 = 82.00; falls on 0.5 boundary.
    out = apply_deload_to_session(
        target_sets=3,
        target_reps_low=5,
        target_reps_high=None,
        last_working_weight_kg=Decimal("102.5"),
        target_rpe_low=None,
        target_rpe_high=None,
    )
    assert out.target_weight_kg == Decimal("82.00")


def test_apply_deload_no_weight_when_no_history() -> None:
    out = apply_deload_to_session(
        target_sets=3,
        target_reps_low=5,
        target_reps_high=None,
        last_working_weight_kg=None,
        target_rpe_low=None,
        target_rpe_high=None,
    )
    assert out.target_weight_kg is None


def test_fatigue_delta_sums_signals() -> None:
    delta = compute_session_fatigue_delta(
        avg_rpe_over_target=True,
        failed_working_sets=2,
        rhr_elevated_3day=True,
    )
    assert delta == Decimal("3.0")  # 1.0 + (0.5 * 2) + 1.0


def test_fatigue_delta_zero_when_clean_session() -> None:
    assert compute_session_fatigue_delta(
        avg_rpe_over_target=False, failed_working_sets=0
    ) == Decimal("0")
