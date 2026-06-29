from seed.programs._dsl import day, exercise, program

SLUGS = {
    "row": "indoor-rowing",
    "jump_rope": "jump-rope",
    "sled": "sled-push",
    "cycling": "cycling",
    "run": "run",
}

template = program(
    slug="hiit-conditioning",
    name="HIIT Conditioning",
    description=(
        "Mixed-modality interval conditioning for cardiovascular fitness and work "
        "capacity: rower, jump rope, sled, and bike intervals, balanced by an easy "
        "aerobic flush. High effort on work days — keep recoveries honest."
    ),
    author="Curated",
    goal="endurance",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Row Intervals",
            exercises=[
                exercise(
                    "row",
                    sets=6,
                    rpe=(8, 9),
                    rest=90,
                    notes="6 × 500m hard, 90s easy row recovery between.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Power Intervals",
            exercises=[
                exercise(
                    "jump_rope",
                    sets=8,
                    rpe=(7, 9),
                    rest=60,
                    notes="8 × 60s fast skipping, 60s rest.",
                ),
                exercise(
                    "sled",
                    sets=6,
                    rpe=(8, 10),
                    rest=90,
                    notes="6 × 20m heavy sled push, walk back as recovery.",
                ),
            ],
        ),
        day(
            "Easy Aerobic",
            exercises=[
                exercise("run", sets=1, rpe=(4, 5), rest=0, notes="25 min easy aerobic flush.")
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Mixed Circuit",
            exercises=[
                exercise(
                    "row", sets=3, rpe=(7, 8), rest=60, notes="3 rounds: 5 min row, 60s rest."
                ),
                exercise(
                    "cycling",
                    sets=3,
                    rpe=(7, 8),
                    rest=60,
                    notes="3 rounds: 5 min hard bike, 60s rest (alternate with the row).",
                ),
            ],
        ),
        day("Rest", is_rest_day=True),
    ],
)
