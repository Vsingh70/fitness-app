"""Progression strategies. Pure functions, no DB access."""

from app.services.progression._types import (
    DoubleInput,
    LinearInput,
    ProgressionDecision,
    ProgressionSet,
    RPEInput,
)
from app.services.progression.double import double_progression
from app.services.progression.linear import linear_progression
from app.services.progression.rpe import rpe_progression

__all__ = [
    "DoubleInput",
    "LinearInput",
    "ProgressionDecision",
    "ProgressionSet",
    "RPEInput",
    "double_progression",
    "linear_progression",
    "rpe_progression",
]
