"""Pure-function helpers in the volume rollup module."""

from __future__ import annotations

from datetime import date

from app.services.analytics.volume import (
    affected_weeks_for_session_dates,
    iso_week_bounds,
    iso_week_for,
)


def test_iso_week_for_dates() -> None:
    # 2026-06-01 is a Monday in ISO week 23.
    assert iso_week_for(date(2026, 6, 1)) == iso_week_for(date(2026, 6, 7))
    iy, iw = iso_week_for(date(2026, 6, 1)).iso_year, iso_week_for(date(2026, 6, 1)).iso_week
    assert iy == 2026
    assert iw == 23


def test_iso_week_bounds_returns_monday_through_sunday() -> None:
    monday, sunday = iso_week_bounds(2026, 23)
    assert monday == date(2026, 6, 1)
    assert sunday == date(2026, 6, 7)


def test_affected_weeks_collapses_duplicate_dates() -> None:
    out = affected_weeks_for_session_dates([date(2026, 6, 1), date(2026, 6, 3), date(2026, 6, 8)])
    assert len(out) == 2  # week 23 and week 24
