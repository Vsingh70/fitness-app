from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import Muscle


class VolumePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iso_year: int
    iso_week: int
    working_sets: Decimal
    tonnage_kg: Decimal
    average_rir: Decimal | None


class VolumeSeries(BaseModel):
    muscle: Muscle
    points: list[VolumePoint]


class VolumeResponse(BaseModel):
    items: list[VolumeSeries]


class CurrentWeekMusclePoint(BaseModel):
    muscle: Muscle
    working_sets: Decimal
    tonnage_kg: Decimal


class CurrentWeekResponse(BaseModel):
    iso_year: int
    iso_week: int
    total_working_sets: Decimal
    total_tonnage_kg: Decimal
    per_muscle: list[CurrentWeekMusclePoint]
