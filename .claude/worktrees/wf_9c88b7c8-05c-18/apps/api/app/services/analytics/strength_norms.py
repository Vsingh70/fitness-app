"""Representative-compound mapping and bodyweight-ratio strength norms.

Each entry is the e1RM / bodyweight ratio at the boundary of the named tier,
roughly aligned with intermediate StrengthLevel-style tables. We use slug
matching so the norms point to canonical exercises from the seed library.

Percentile interpretation (used by app.services.analytics.insights):
- score < bw_ratio at 25% -> bottom quartile (weak)
- score >= bw_ratio at 75% -> top quartile (strong)

Subjects in `MUSCLE_TO_REPRESENTATIVE_SLUG` are listed in priority order. We
take the first slug the user has actually logged in the lookback window.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import Muscle, SexAtBirth


@dataclass(frozen=True)
class StrengthBand:
    p25: Decimal  # boundary for bottom quartile
    p50: Decimal
    p75: Decimal  # boundary for top quartile


# Boundaries are e1RM / bodyweight for an intermediate trainee.
# Source: simplified StrengthLevel intermediate band ratios, halved to be more
# realistic for the average lifter rather than competitive PL norms.
_MALE_BANDS: dict[str, StrengthBand] = {
    "barbell-bench-press": StrengthBand(Decimal("0.75"), Decimal("1.10"), Decimal("1.40")),
    "barbell-back-squat": StrengthBand(Decimal("1.00"), Decimal("1.50"), Decimal("1.90")),
    "barbell-deadlift": StrengthBand(Decimal("1.25"), Decimal("1.75"), Decimal("2.20")),
    "barbell-romanian-deadlift": StrengthBand(Decimal("1.00"), Decimal("1.40"), Decimal("1.80")),
    "barbell-overhead-press": StrengthBand(Decimal("0.50"), Decimal("0.75"), Decimal("1.00")),
    "pull-up": StrengthBand(Decimal("0.05"), Decimal("0.20"), Decimal("0.50")),
    "barbell-row": StrengthBand(Decimal("0.60"), Decimal("0.90"), Decimal("1.20")),
    "barbell-curl": StrengthBand(Decimal("0.30"), Decimal("0.50"), Decimal("0.70")),
}

_FEMALE_BANDS: dict[str, StrengthBand] = {
    "barbell-bench-press": StrengthBand(Decimal("0.40"), Decimal("0.65"), Decimal("0.90")),
    "barbell-back-squat": StrengthBand(Decimal("0.65"), Decimal("1.00"), Decimal("1.40")),
    "barbell-deadlift": StrengthBand(Decimal("0.85"), Decimal("1.30"), Decimal("1.70")),
    "barbell-romanian-deadlift": StrengthBand(Decimal("0.70"), Decimal("1.05"), Decimal("1.40")),
    "barbell-overhead-press": StrengthBand(Decimal("0.30"), Decimal("0.50"), Decimal("0.70")),
    "pull-up": StrengthBand(Decimal("0.02"), Decimal("0.10"), Decimal("0.30")),
    "barbell-row": StrengthBand(Decimal("0.40"), Decimal("0.65"), Decimal("0.90")),
    "barbell-curl": StrengthBand(Decimal("0.20"), Decimal("0.35"), Decimal("0.50")),
}


def _avg_bands(a: StrengthBand, b: StrengthBand) -> StrengthBand:
    return StrengthBand(
        p25=((a.p25 + b.p25) / Decimal("2")).quantize(Decimal("0.01")),
        p50=((a.p50 + b.p50) / Decimal("2")).quantize(Decimal("0.01")),
        p75=((a.p75 + b.p75) / Decimal("2")).quantize(Decimal("0.01")),
    )


def get_band(slug: str, sex: SexAtBirth | None) -> StrengthBand | None:
    """Look up the band for a given exercise slug and user sex.

    Returns None for slugs we don't have norms for. "other" or unknown uses the
    average of male and female bands.
    """
    if sex == SexAtBirth.male:
        return _MALE_BANDS.get(slug)
    if sex == SexAtBirth.female:
        return _FEMALE_BANDS.get(slug)
    male = _MALE_BANDS.get(slug)
    female = _FEMALE_BANDS.get(slug)
    if male is None or female is None:
        return None
    return _avg_bands(male, female)


# Each muscle maps to candidate exercise slugs in priority order (best
# representative first). The heuristic picks the first slug the user has
# actually logged in the lookback window.
MUSCLE_TO_REPRESENTATIVE_SLUG: dict[Muscle, tuple[str, ...]] = {
    Muscle.chest: ("barbell-bench-press",),
    Muscle.quads: ("barbell-back-squat",),
    Muscle.hamstrings: ("barbell-romanian-deadlift", "barbell-deadlift"),
    Muscle.glutes: ("barbell-deadlift", "barbell-back-squat"),
    Muscle.lats: ("pull-up", "barbell-row"),
    Muscle.front_delts: ("barbell-overhead-press", "barbell-bench-press"),
    Muscle.rhomboids: ("barbell-row",),
    Muscle.biceps: ("barbell-curl",),
}


def classify(score: Decimal, band: StrengthBand) -> str:
    """Return 'weak' if score < p25, 'strong' if >= p75, 'moderate' otherwise."""
    if score < band.p25:
        return "weak"
    if score >= band.p75:
        return "strong"
    return "moderate"
