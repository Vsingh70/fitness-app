from seed.programs._dsl import day, exercise, program

SLUGS = {
    "swim": "lap-swimming",
    "cycling": "cycling",
    "run": "run",
}

template = program(
    slug="triathlon-sprint-base",
    name="Sprint Triathlon Base",
    description=(
        "A three-sport base week for sprint-distance triathlon: one focused swim, "
        "bike, and run, a bike→run brick to practice the transition, and a long "
        "endurance ride. Build volume gradually before race-specific work."
    ),
    author="Curated",
    goal="endurance",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Swim",
            exercises=[
                exercise(
                    "swim",
                    sets=8,
                    rpe=(6, 8),
                    rest=30,
                    notes="200m warmup; 8 × 100m steady; 100m cooldown.",
                )
            ],
        ),
        day(
            "Bike",
            exercises=[
                exercise("cycling", sets=1, rpe=(5, 6), rest=0, notes="60 min Zone-2 endurance.")
            ],
        ),
        day(
            "Run",
            exercises=[
                exercise("run", sets=1, rpe=(4, 5), rest=0, notes="30–40 min easy aerobic run.")
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Brick (Bike → Run)",
            exercises=[
                exercise(
                    "cycling",
                    sets=1,
                    rpe=(6, 7),
                    rest=0,
                    notes="45 min ride at moderate effort, then transition straight to the run.",
                ),
                exercise(
                    "run",
                    sets=1,
                    rpe=(6, 7),
                    rest=0,
                    notes="15 min run immediately off the bike; settle into goal race pace.",
                ),
            ],
        ),
        day(
            "Long Ride",
            exercises=[
                exercise(
                    "cycling",
                    sets=1,
                    rpe=(5, 6),
                    rest=0,
                    notes="90 min endurance; practice fueling.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
    ],
)
