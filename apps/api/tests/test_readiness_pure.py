"""Pure tests for the readiness formula + band classifier."""

from __future__ import annotations

from decimal import Decimal

from app.services.readiness import compute_readiness_score, severity_band


def test_severity_bands_at_boundaries() -> None:
    assert severity_band(0) == "low"
    assert severity_band(40) == "low"
    assert severity_band(41) == "moderate"
    assert severity_band(70) == "moderate"
    assert severity_band(71) == "high"
    assert severity_band(100) == "high"


def test_perfect_signals_with_hrv_returns_100() -> None:
    breakdown = compute_readiness_score(
        sleep_minutes=480,
        rhr=60,
        hrv_ms=Decimal("60"),
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=Decimal("60"),
    )
    assert breakdown.score == 100
    assert breakdown.band == "high"
    assert breakdown.hrv_used is True
    assert breakdown.sleep_component == Decimal("40.00")
    assert breakdown.rhr_component == Decimal("30.00")
    assert breakdown.hrv_component == Decimal("30.00")


def test_sleep_component_clips_at_one() -> None:
    """10 hours of sleep should not exceed 40."""
    breakdown = compute_readiness_score(
        sleep_minutes=600,
        rhr=60,
        hrv_ms=Decimal("60"),
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=Decimal("60"),
    )
    assert breakdown.sleep_component == Decimal("40.00")


def test_rhr_elevated_zero_component() -> None:
    """RHR 10 BPM above baseline drops the component to 0."""
    breakdown = compute_readiness_score(
        sleep_minutes=480,
        rhr=70,
        hrv_ms=Decimal("60"),
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=Decimal("60"),
    )
    assert breakdown.rhr_component == Decimal("0.00")
    # 40 + 0 + 30 = 70 -> moderate.
    assert breakdown.score == 70
    assert breakdown.band == "moderate"


def test_hrv_missing_redistributes_to_sleep_and_rhr() -> None:
    """Without HRV, sleep weight is 55 and rhr is 45. Perfect sleep + rhr -> 100."""
    breakdown = compute_readiness_score(
        sleep_minutes=480,
        rhr=60,
        hrv_ms=None,
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=None,
    )
    assert breakdown.hrv_used is False
    assert breakdown.sleep_component == Decimal("55.00")
    assert breakdown.rhr_component == Decimal("45.00")
    assert breakdown.score == 100


def test_hrv_present_but_baseline_missing_redistributes() -> None:
    """HRV today but no baseline -> redistribute since we can't normalize."""
    breakdown = compute_readiness_score(
        sleep_minutes=480,
        rhr=60,
        hrv_ms=Decimal("60"),
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=None,
    )
    assert breakdown.hrv_used is False
    assert breakdown.sleep_component == Decimal("55.00")
    assert breakdown.rhr_component == Decimal("45.00")


def test_all_signals_zero_returns_low_score() -> None:
    breakdown = compute_readiness_score(
        sleep_minutes=0,
        rhr=None,
        hrv_ms=None,
        baseline_rhr=None,
        baseline_hrv_ms=None,
    )
    assert breakdown.score == 0
    assert breakdown.band == "low"


def test_low_band_boundary_at_40() -> None:
    """Tune sleep to land exactly at 40 + 0 + 0 = 40 (low band)."""
    # 480 minutes * 1.0 * 55 = 55, too high. With HRV usable: 480 * 40 = 40.
    breakdown = compute_readiness_score(
        sleep_minutes=480,
        rhr=70,  # 10 BPM above baseline -> 0
        hrv_ms=Decimal("0"),  # ratio 0 -> 0
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=Decimal("60"),
    )
    # 40 + 0 + 0 = 40 -> low band.
    assert breakdown.score == 40
    assert breakdown.band == "low"


def test_partial_sleep_proportional() -> None:
    """4 hours of sleep = 50% -> sleep component is 20 (with HRV) or 27.5 without."""
    breakdown = compute_readiness_score(
        sleep_minutes=240,
        rhr=60,
        hrv_ms=Decimal("60"),
        baseline_rhr=Decimal("60"),
        baseline_hrv_ms=Decimal("60"),
    )
    assert breakdown.sleep_component == Decimal("20.00")
    assert breakdown.score == 80  # 20 + 30 + 30
