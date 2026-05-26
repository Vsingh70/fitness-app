from enum import StrEnum


class UnitSystem(StrEnum):
    metric = "metric"
    imperial = "imperial"


class SexAtBirth(StrEnum):
    male = "male"
    female = "female"
    other = "other"
