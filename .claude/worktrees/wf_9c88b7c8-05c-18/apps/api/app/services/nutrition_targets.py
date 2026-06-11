"""Default macro targets via Mifflin-St Jeor when no meal plan is active.

Inputs:
- age (derived from User.birthdate)
- sex_at_birth (User.sex_at_birth; "other"/None falls back to avg of M+F)
- height_cm (User.height_cm)
- latest weight_kg from body_metrics
- activity factor (default 1.55)

Outputs: maintenance kcal, protein g (2.0 g/kg), fat g (25% of kcal / 9),
carbs g (remainder / 4). Returns None if any required input is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.body_metric import BodyMetric
from app.models.enums import SexAtBirth
from app.models.user import User

DEFAULT_ACTIVITY_FACTOR = Decimal("1.55")
PROTEIN_G_PER_KG = Decimal("2.0")
FAT_PCT_OF_KCAL = Decimal("0.25")
KCAL_PER_G_FAT = Decimal("9")
KCAL_PER_G_CARB = Decimal("4")


@dataclass(frozen=True)
class MacroTargets:
    target_kcal: Decimal
    target_protein_g: Decimal
    target_carbs_g: Decimal
    target_fat_g: Decimal
    source: str  # "plan" | "default"


def _age_years(birthdate: date | None, *, today: date | None = None) -> int | None:
    if birthdate is None:
        return None
    today = today or datetime.now(tz=UTC).date()
    years = today.year - birthdate.year
    if (today.month, today.day) < (birthdate.month, birthdate.day):
        years -= 1
    return max(0, years)


def _mifflin_st_jeor(
    *, weight_kg: Decimal, height_cm: Decimal, age: int, sex: SexAtBirth | None
) -> Decimal:
    """BMR in kcal/day. Sex 'other' or unknown uses the average of M and F."""
    weight = Decimal(weight_kg)
    height = Decimal(height_cm)
    base = Decimal("10") * weight + Decimal("6.25") * height - Decimal("5") * Decimal(age)
    if sex == SexAtBirth.male:
        return base + Decimal("5")
    if sex == SexAtBirth.female:
        return base - Decimal("161")
    # other / unknown: average of male + female adjustments = (5 + -161) / 2 = -78
    return base - Decimal("78")


async def _latest_weight_kg(session: AsyncSession, user_id: UUID) -> Decimal | None:
    row = (
        await session.execute(
            select(BodyMetric.weight_kg)
            .where(BodyMetric.user_id == user_id, BodyMetric.weight_kg.is_not(None))
            .order_by(BodyMetric.recorded_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    value = row[0]
    return None if value is None else Decimal(value)


async def derive_default_targets(
    session: AsyncSession,
    user: User,
    *,
    today: date | None = None,
    activity_factor: Decimal = DEFAULT_ACTIVITY_FACTOR,
) -> MacroTargets | None:
    """Compute Mifflin-St Jeor based targets. Returns None if any required
    profile field is missing (birthdate, height_cm, latest weight).
    """
    weight = await _latest_weight_kg(session, user.id)
    if weight is None or weight <= 0:
        return None
    if user.height_cm is None or user.height_cm <= 0:
        return None
    age = _age_years(user.birthdate, today=today)
    if age is None:
        return None

    bmr = _mifflin_st_jeor(
        weight_kg=weight, height_cm=user.height_cm, age=age, sex=user.sex_at_birth
    )
    kcal = (bmr * activity_factor).quantize(Decimal("0.01"))
    protein_g = (weight * PROTEIN_G_PER_KG).quantize(Decimal("0.01"))
    fat_kcal = (kcal * FAT_PCT_OF_KCAL).quantize(Decimal("0.01"))
    fat_g = (fat_kcal / KCAL_PER_G_FAT).quantize(Decimal("0.01"))
    protein_kcal = (protein_g * Decimal("4")).quantize(Decimal("0.01"))
    carb_kcal = kcal - fat_kcal - protein_kcal
    if carb_kcal < 0:
        carb_kcal = Decimal("0")
    carbs_g = (carb_kcal / KCAL_PER_G_CARB).quantize(Decimal("0.01"))
    return MacroTargets(
        target_kcal=kcal,
        target_protein_g=protein_g,
        target_carbs_g=carbs_g,
        target_fat_g=fat_g,
        source="default",
    )
