from seed.programs._dsl import day, exercise, program

SLUGS = {
    "run": "run",
    "cycling": "cycling",
}

template = program(
    slug="run-5k-starter",
    name="5K Starter (Run/Walk)",
    description=(
        "An eight-week-friendly run/walk plan that builds a true beginner up to a "
        "continuous 5K. Three easy run sessions plus a low-impact cross-train day, "
        "with run intervals lengthening as walk breaks shrink."
    ),
    author="Curated",
    goal="endurance",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Run/Walk A",
            exercises=[
                exercise(
                    "run",
                    sets=1,
                    rpe=(4, 6),
                    rest=0,
                    notes="Alternate 2 min easy jog / 1 min walk × 8 rounds (~24 min total).",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Cross-Train",
            exercises=[
                exercise(
                    "cycling",
                    sets=1,
                    rpe=(3, 5),
                    rest=0,
                    notes="25–30 min easy spin, low resistance — keep it conversational.",
                )
            ],
        ),
        day(
            "Run/Walk B",
            exercises=[
                exercise(
                    "run",
                    sets=1,
                    rpe=(4, 6),
                    rest=0,
                    notes="3 min jog / 1 min walk × 6 rounds; keep breathing steady.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Long Run/Walk",
            exercises=[
                exercise(
                    "run",
                    sets=1,
                    rpe=(4, 6),
                    rest=0,
                    notes="Build to 30–35 min total; take walk breaks as needed.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
    ],
)
