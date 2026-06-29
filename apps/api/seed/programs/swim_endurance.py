from seed.programs._dsl import day, exercise, program

SLUGS = {
    "swim": "lap-swimming",
}

template = program(
    slug="swim-endurance",
    name="Swim Endurance",
    description=(
        "Three-to-four pool sessions a week to build freestyle aerobic capacity: a "
        "technique/drill day, steady continuous swims, one interval set, and a long "
        "continuous swim. Distances scale to your level."
    ),
    author="Curated",
    goal="endurance",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Technique Swim",
            exercises=[
                exercise(
                    "swim",
                    sets=1,
                    rpe=(4, 6),
                    rest=0,
                    notes="200m easy warmup; 8 × 50m drills (catch-up, fingertip drag); 200m easy.",
                )
            ],
        ),
        day(
            "Endurance Swim",
            exercises=[
                exercise(
                    "swim",
                    sets=1,
                    rpe=(5, 7),
                    rest=0,
                    notes="Continuous 1000–1500m steady freestyle, relaxed breathing rhythm.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Interval Swim",
            exercises=[
                exercise(
                    "swim",
                    sets=10,
                    rpe=(7, 9),
                    rest=30,
                    notes="10 × 100m at moderate-hard effort, 30s rest on the wall.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Long Swim",
            exercises=[
                exercise(
                    "swim",
                    sets=1,
                    rpe=(5, 6),
                    rest=0,
                    notes="Continuous 2000m+ aerobic; sight/turn every few laps, even pacing.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
    ],
)
