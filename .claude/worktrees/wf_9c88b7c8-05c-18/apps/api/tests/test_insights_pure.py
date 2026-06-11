"""Pure tests for the strength norms table, regression math, and the per-
finding boundary classifiers.
"""

from __future__ import annotations

from decimal import Decimal

from app.models.enums import Muscle, SexAtBirth
from app.services.analytics import strength_norms
from app.services.analytics.insights import (
    _linear_regression_slope,
    compute_imbalance_findings,
    compute_undertrained_findings,
)

# Strength norms ------------------------------------------------------------


def test_get_band_returns_band_for_known_slug_male() -> None:
    band = strength_norms.get_band("barbell-bench-press", SexAtBirth.male)
    assert band is not None
    assert band.p25 < band.p50 < band.p75


def test_get_band_returns_average_for_other() -> None:
    male = strength_norms.get_band("barbell-bench-press", SexAtBirth.male)
    female = strength_norms.get_band("barbell-bench-press", SexAtBirth.female)
    other = strength_norms.get_band("barbell-bench-press", SexAtBirth.other)
    assert other is not None
    assert male is not None
    assert female is not None
    assert other.p25 == ((male.p25 + female.p25) / Decimal("2")).quantize(Decimal("0.01"))


def test_get_band_returns_none_for_unknown_slug() -> None:
    assert strength_norms.get_band("not-a-real-exercise", SexAtBirth.male) is None


def test_classify_at_band_boundaries() -> None:
    band = strength_norms.StrengthBand(p25=Decimal("1.0"), p50=Decimal("1.5"), p75=Decimal("2.0"))
    # Strictly below p25 -> weak.
    assert strength_norms.classify(Decimal("0.99"), band) == "weak"
    # Exactly p25 -> moderate (we use strict less-than).
    assert strength_norms.classify(Decimal("1.0"), band) == "moderate"
    # Exactly p75 -> strong (we use >=).
    assert strength_norms.classify(Decimal("2.0"), band) == "strong"
    # Above p75 -> strong.
    assert strength_norms.classify(Decimal("2.5"), band) == "strong"
    # In between -> moderate.
    assert strength_norms.classify(Decimal("1.5"), band) == "moderate"


# Regression math ----------------------------------------------------------


def test_regression_slope_flat_series_is_zero() -> None:
    xs = [Decimal(x) for x in range(8)]
    ys = [Decimal("100")] * 8
    slope, stddev = _linear_regression_slope(xs, ys)
    assert slope == Decimal("0.0000")
    assert stddev == Decimal("0")


def test_regression_slope_positive_when_improving() -> None:
    xs = [Decimal(x) for x in range(6)]
    ys = [Decimal("100") + Decimal(x) * Decimal("2.5") for x in range(6)]
    slope, _ = _linear_regression_slope(xs, ys)
    assert slope > 0


def test_regression_slope_negative_when_regressing() -> None:
    xs = [Decimal(x) for x in range(6)]
    ys = [Decimal("100") - Decimal(x) for x in range(6)]
    slope, _ = _linear_regression_slope(xs, ys)
    assert slope < 0


# Imbalance ----------------------------------------------------------------


def test_imbalance_inside_thresholds_emits_nothing() -> None:
    sets_by_muscle = {
        Muscle.chest: Decimal("10"),
        Muscle.front_delts: Decimal("4"),
        Muscle.triceps: Decimal("4"),
        Muscle.lats: Decimal("10"),
        Muscle.rhomboids: Decimal("4"),
        Muscle.rear_delts: Decimal("3"),
        Muscle.biceps: Decimal("3"),
        Muscle.quads: Decimal("10"),
        Muscle.hamstrings: Decimal("10"),
    }
    out = compute_imbalance_findings(sets_by_muscle)
    assert out == []


def test_imbalance_push_pull_outside_high() -> None:
    """push 30, pull 10 -> ratio 3.0, outside 1.4 high."""
    sets_by_muscle = {
        Muscle.chest: Decimal("30"),
        Muscle.front_delts: Decimal("0"),
        Muscle.triceps: Decimal("0"),
        Muscle.lats: Decimal("10"),
        Muscle.rhomboids: Decimal("0"),
        Muscle.rear_delts: Decimal("0"),
        Muscle.biceps: Decimal("0"),
    }
    out = compute_imbalance_findings(sets_by_muscle)
    subjects = {f.subject for f in out}
    assert "push_vs_pull" in subjects


def test_imbalance_quads_vs_hamstrings_outside_low() -> None:
    """quads 5, hamstrings 12 -> ratio 0.42, below 0.6."""
    sets_by_muscle = {
        Muscle.quads: Decimal("5"),
        Muscle.hamstrings: Decimal("12"),
    }
    out = compute_imbalance_findings(sets_by_muscle)
    subjects = {f.subject for f in out}
    assert "quads_vs_hamstrings" in subjects


def test_imbalance_zero_denominator_skipped() -> None:
    """Zero pull volume -> no push/pull insight (avoid div by zero)."""
    sets_by_muscle = {
        Muscle.chest: Decimal("10"),
        Muscle.lats: Decimal("0"),
    }
    out = compute_imbalance_findings(sets_by_muscle)
    assert all(f.subject != "push_vs_pull" for f in out)


# Undertrained ------------------------------------------------------------


def test_undertrained_at_threshold_does_not_fire() -> None:
    """Boundary: avg = 8.00 across 4 weeks (32 sets) -> not undertrained."""
    sets_by_muscle = {Muscle.chest: Decimal("32")}
    out = compute_undertrained_findings(sets_by_muscle, lookback_weeks=4)
    assert all(f.muscle != Muscle.chest for f in out)


def test_undertrained_just_below_threshold_fires() -> None:
    """avg = 7.75 -> undertrained."""
    sets_by_muscle = {Muscle.chest: Decimal("31")}
    out = compute_undertrained_findings(sets_by_muscle, lookback_weeks=4)
    chest = [f for f in out if f.muscle == Muscle.chest]
    assert len(chest) == 1
    assert chest[0].avg_weekly_sets == Decimal("7.75")


def test_undertrained_missing_muscle_treats_as_zero() -> None:
    out = compute_undertrained_findings({}, lookback_weeks=4)
    # All primary movers should show up as undertrained.
    assert any(f.muscle == Muscle.chest for f in out)
    assert any(f.muscle == Muscle.lats for f in out)
