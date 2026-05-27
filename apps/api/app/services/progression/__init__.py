"""Progression strategies. Pure functions, no DB access."""

from app.services.progression._types import (
    DoubleInput,
    LinearInput,
    ProgressionDecision,
    ProgressionSet,
)
from app.services.progression.double import double_progression
from app.services.progression.linear import linear_progression

__all__ = [
    "DoubleInput",
    "LinearInput",
    "ProgressionDecision",
    "ProgressionSet",
    "double_progression",
    "linear_progression",
]
