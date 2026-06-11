"""Pure-function tests for RPE-based progression."""

from __future__ import annotations

from decimal import Decimal

from app.services.progression import (
    ProgressionSet,
    RPEInput,
    rpe_progression,
)


def _set(weight: str, reps: int, *, working: bool = True) -> ProgressionSet:
    return ProgressionSet(weight_kg=Decimal(weight), reps=reps, is_working=working)


def _input(
    *,
    sets: list[ProgressionSet],
    set_rpes: list[Decimal | None],
    set_rirs: list[int | None] | None = None,
    target_rpe_low: str = "7",
    target_rpe_high: str = "8",
    target_reps_low: int = 5,
    target_reps_high: int | None = 5,
    current_weight: str = "100",
    consecutive_above: int = 0,
    recent_e1rm: list[Decimal] | None = None,
) -> RPEInput:
    return RPEInput(
        last_session_sets=sets,
        set_rpes=set_rpes,
        set_rirs=set_rirs if set_rirs is not None else [None] * len(sets),
        target_rpe_low=Decimal(target_rpe_low),
        target_rpe_high=Decimal(target_rpe_high),
        target_reps_low=target_reps_low,
        target_reps_high=target_reps_high,
        increment_pct=Decimal("0.025"),
        current_weight_kg=Decimal(current_weight),
        consecutive_above=consecutive_above,
        recent_e1rm=recent_e1rm or [],
    )


# ---------------------------------------------------------------------------
# Below target range -> increase weight
# ---------------------------------------------------------------------------


def test_well_below_range_increases_weight() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5), _set("100", 5)],
            set_rpes=[Decimal("6"), Decimal("6"), Decimal("6")],
            current_weight="100",
        )
    )
    # 100 * 1.025 = 102.50 -> quantized to 102.50 (nearest 0.5)
    assert decision.next_weight_kg == Decimal("102.50")
    assert decision.is_deload is False
    assert decision.rationale_key == "rpe.advance.below_range"
    assert decision.consecutive_above == 0
    assert decision.consecutive_successes == 1


# ---------------------------------------------------------------------------
# Within range
# ---------------------------------------------------------------------------


def test_within_range_below_reps_high_adds_rep_to_lowest() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 4), _set("100", 4)],
            set_rpes=[Decimal("7"), Decimal("7.5"), Decimal("8")],
            target_reps_low=5,
            target_reps_high=6,
            current_weight="100",
        )
    )
    assert decision.next_weight_kg == Decimal("100")
    # lowest is 4 -> +1 = 5
    assert decision.next_reps_low == 5
    assert decision.rationale_key == "rpe.add_rep.in_range"


def test_within_range_at_top_advances_weight() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 8), _set("100", 8), _set("100", 8)],
            set_rpes=[Decimal("7"), Decimal("7.5"), Decimal("8")],
            target_reps_low=6,
            target_reps_high=8,
            current_weight="100",
        )
    )
    # avg RPE = 7.5, within [7,8], reps_high hit on all -> increase weight
    assert decision.next_weight_kg == Decimal("102.50")
    assert decision.rationale_key == "rpe.advance.in_range_top"


# ---------------------------------------------------------------------------
# Above range
# ---------------------------------------------------------------------------


def test_slightly_above_range_holds_weight() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5), _set("100", 5)],
            set_rpes=[Decimal("8.5"), Decimal("8.5"), Decimal("8.5")],
            current_weight="100",
        )
    )
    assert decision.next_weight_kg == Decimal("100")
    assert decision.is_deload is False
    assert decision.rationale_key == "rpe.hold.slightly_above"
    assert decision.consecutive_above == 1


def test_far_above_range_backs_off_5pct() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5), _set("100", 5)],
            set_rpes=[Decimal("9.5"), Decimal("9.5"), Decimal("9.5")],
            current_weight="100",
        )
    )
    # 100 * 0.95 = 95.00
    assert decision.next_weight_kg == Decimal("95.00")
    assert decision.is_deload is False
    assert decision.rationale_key == "rpe.back_off.far_above"
    assert decision.consecutive_above == 1


def test_three_consecutive_above_triggers_deload() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5), _set("100", 5)],
            set_rpes=[Decimal("8.5"), Decimal("8.5"), Decimal("8.5")],
            current_weight="100",
            consecutive_above=2,
        )
    )
    assert decision.is_deload is True
    assert decision.next_weight_kg == Decimal("95.00")
    assert decision.consecutive_above == 0
    assert decision.rationale_key == "rpe.deload.consecutive_above"


# ---------------------------------------------------------------------------
# e1RM sanity cap
# ---------------------------------------------------------------------------


def test_e1rm_cap_kicks_in_on_big_jump() -> None:
    """If recent e1RMs cluster around ~120 kg and the next rec would imply
    140 kg e1RM, the cap should pull the next weight down to imply ~123 kg."""
    # 120 kg * (1 + 5/30) = 140 kg implied e1RM at 5 reps
    # Median of recent = 110. Cap = 110 * 1.025 = 112.75
    # Allowed weight at 5 reps = 112.75 / (1 + 5/30) = 96.64...
    decision = rpe_progression(
        _input(
            sets=[_set("120", 5), _set("120", 5), _set("120", 5)],
            set_rpes=[Decimal("6"), Decimal("6"), Decimal("6")],
            target_reps_low=5,
            target_reps_high=5,
            current_weight="120",
            recent_e1rm=[Decimal("108"), Decimal("110"), Decimal("112")],
        )
    )
    # Implied would be 123 * (1 + 5/30) = 143.5; capped at 112.75 -> 96.5 kg quantized
    assert decision.next_weight_kg <= Decimal("100")
    # And the rec is still an advance (rationale key) since rpe was below range.
    assert decision.rationale_key == "rpe.advance.below_range"


def test_e1rm_cap_skipped_with_too_little_history() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5), _set("100", 5)],
            set_rpes=[Decimal("6"), Decimal("6"), Decimal("6")],
            current_weight="100",
            recent_e1rm=[Decimal("110")],
        )
    )
    # Cap silently skipped -> normal 2.5% bump
    assert decision.next_weight_kg == Decimal("102.50")


# ---------------------------------------------------------------------------
# RIR fallback
# ---------------------------------------------------------------------------


def test_rir_fallback_when_rpe_missing() -> None:
    # All sets have RIR 4 (effective RPE = 6) but no RPE -> well below 7-8.
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5), _set("100", 5)],
            set_rpes=[None, None, None],
            set_rirs=[4, 4, 4],
            current_weight="100",
        )
    )
    assert decision.next_weight_kg == Decimal("102.50")
    assert decision.rationale_key == "rpe.advance.below_range"


def test_rpe_preferred_over_rir_when_both_present() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5), _set("100", 5)],
            set_rpes=[Decimal("9"), Decimal("9")],
            set_rirs=[1, 1],  # would be 9 too; consistent
            current_weight="100",
        )
    )
    # avg 9.0, target_high 8 -> slightly above (by 1.0, exactly at threshold)
    assert decision.rationale_key == "rpe.hold.slightly_above"


def test_top_set_excludes_back_off_sets() -> None:
    """Sets at lower weight are ignored when computing top-set RPE."""
    # Top set at 110 with RPE 6.5 (below range); back-off at 95 with RPE 9.
    decision = rpe_progression(
        _input(
            sets=[_set("110", 5), _set("95", 8), _set("95", 8)],
            set_rpes=[Decimal("6.5"), Decimal("9"), Decimal("9")],
            current_weight="110",
        )
    )
    # Should use only the 110 set -> avg 6.5 -> increase weight.
    assert decision.rationale_key == "rpe.advance.below_range"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_working_sets_holds() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5, working=False)],
            set_rpes=[Decimal("8")],
            current_weight="100",
        )
    )
    assert decision.next_weight_kg == Decimal("100")
    assert decision.rationale_key == "rpe.hold.no_data"


def test_no_rpe_or_rir_holds() -> None:
    decision = rpe_progression(
        _input(
            sets=[_set("100", 5)],
            set_rpes=[None],
            set_rirs=[None],
            current_weight="100",
        )
    )
    assert decision.next_weight_kg == Decimal("100")
    assert decision.rationale_key == "rpe.hold.no_rpe"
