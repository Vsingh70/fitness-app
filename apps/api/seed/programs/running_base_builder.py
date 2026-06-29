from seed.programs._dsl import day, exercise, program

SLUGS = {
    "run": "run",
}

template = program(
    slug="running-base-builder",
    name="Running Base Builder",
    description=(
        "A balanced weekly running structure for 5K–half-marathon: easy aerobic "
        "miles, one tempo session, one interval session, and a weekly long run. "
        "Most of the volume stays easy; only two days are hard."
    ),
    author="Curated",
    goal="endurance",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Easy Run",
            exercises=[
                exercise("run", sets=1, rpe=(4, 5), rest=0, notes="40 min at conversational pace.")
            ],
        ),
        day(
            "Tempo Run",
            exercises=[
                exercise(
                    "run",
                    sets=1,
                    rpe=(7, 8),
                    rest=0,
                    notes="10 min warmup, 20 min @ comfortably-hard tempo, 10 min cooldown.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Intervals",
            exercises=[
                exercise(
                    "run",
                    sets=6,
                    rpe=(8, 9),
                    rest=120,
                    notes="6 × 800m at ~5K effort, 2 min easy jog recovery between reps.",
                )
            ],
        ),
        day(
            "Easy Run + Strides",
            exercises=[
                exercise(
                    "run",
                    sets=1,
                    rpe=(4, 5),
                    rest=0,
                    notes="30 min easy, finish with 4–6 × 20s relaxed strides.",
                )
            ],
        ),
        day(
            "Long Run",
            exercises=[
                exercise(
                    "run",
                    sets=1,
                    rpe=(5, 6),
                    rest=0,
                    notes="75–90 min easy/steady; add 5–10 min each week, then cut back every 4th.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
    ],
)
