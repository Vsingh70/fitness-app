from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.meal import BodyMetricResponse, MealResponse
from app.schemas.program import ProgramResponse
from app.schemas.user import MeResponse
from app.schemas.workout import WorkoutSessionResponse

# Bump this when the bundle shape changes in a backwards-incompatible way.
EXPORT_SCHEMA_VERSION = 1


class ExportBundle(BaseModel):
    """Full account data export for compliance + portability.

    A single JSON document containing every row the user owns across the
    primary domains: workout sessions (+ exercises + sets), meals (+ items),
    body metrics, and programs (+ days + exercises).
    """

    schema_version: int = Field(
        default=EXPORT_SCHEMA_VERSION,
        description="Version of the export bundle format.",
    )
    exported_at: datetime = Field(description="When this bundle was generated (UTC).")

    user: MeResponse
    workout_sessions: list[WorkoutSessionResponse]
    meals: list[MealResponse]
    body_metrics: list[BodyMetricResponse]
    programs: list[ProgramResponse]
