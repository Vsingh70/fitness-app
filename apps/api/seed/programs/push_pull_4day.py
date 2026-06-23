from seed.programs._dsl import day, exercise, program

SLUGS = {
    "bench": "barbell-bench-press-medium-grip",
    "ohp": "barbell-shoulder-press",
    "incline_db": "incline-dumbbell-press",
    "lateral_raise": "side-lateral-raise",
    "triceps_pushdown": "triceps-pushdown",
    "overhead_triceps_ext": "cable-rope-overhead-triceps-extension",
    "deadlift": "barbell-deadlift",
    "pull_up": "pullups",
    "barbell_row": "bent-over-barbell-row",
    "lat_pulldown": "wide-grip-lat-pulldown",
    "face_pull": "face-pull",
    "barbell_curl": "barbell-curl",
    "hammer_curl": "alternate-hammer-curl",
    "squat": "barbell-squat",
    "rdl": "romanian-deadlift",
    "leg_press": "leg-press",
    "leg_curl": "lying-leg-curls",
    "leg_extension": "leg-extensions",
    "standing_calf": "standing-calf-raises",
    "hanging_leg_raise": "hanging-leg-raise",
}

template = program(
    slug="push-pull-4day",
    name="Push Pull (4-day)",
    description=(
        "Alternating push (upper push + legs) and pull (upper pull + posterior chain) "
        "days, four times a week."
    ),
    author="Curated",
    goal="general",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Push A",
            exercises=[
                exercise(
                    "bench",
                    sets=4,
                    reps=(6, 10),
                    rpe=(7, 8),
                    rest=150,
                    progression="double_progression",
                ),
                exercise(
                    "ohp",
                    sets=3,
                    reps=(6, 10),
                    rpe=(7, 8),
                    rest=150,
                    progression="double_progression",
                ),
                exercise("incline_db", sets=3, reps=(8, 12), rpe=(7, 9), rest=120),
                exercise("squat", sets=4, reps=(5, 8), rpe=(7, 8), rest=240, progression="linear"),
                exercise("leg_extension", sets=3, reps=(12, 20), rpe=(8, 10), rest=60),
                exercise("triceps_pushdown", sets=3, reps=(10, 15), rpe=(8, 9), rest=75),
            ],
        ),
        day(
            "Pull A",
            exercises=[
                exercise(
                    "deadlift", sets=3, reps=(3, 5), rpe=(7, 8), rest=240, progression="linear"
                ),
                exercise(
                    "pull_up",
                    sets=4,
                    reps=(5, 10),
                    rpe=(7, 9),
                    rest=150,
                    progression="double_progression",
                ),
                exercise("barbell_row", sets=3, reps=(6, 10), rpe=(7, 9), rest=150),
                exercise("rdl", sets=3, reps=(8, 12), rpe=(7, 8), rest=120),
                exercise("face_pull", sets=3, reps=(12, 20), rpe=(8, 10), rest=60),
                exercise("barbell_curl", sets=3, reps=(8, 12), rpe=(8, 9), rest=75),
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Push B",
            exercises=[
                exercise(
                    "ohp",
                    sets=4,
                    reps=(5, 8),
                    rpe=(7, 8),
                    rest=180,
                    progression="double_progression",
                ),
                exercise("bench", sets=3, reps=(8, 12), rpe=(7, 9), rest=150),
                exercise("lateral_raise", sets=4, reps=(12, 20), rpe=(8, 10), rest=60),
                exercise("leg_press", sets=4, reps=(10, 15), rpe=(8, 9), rest=120),
                exercise("standing_calf", sets=4, reps=(8, 12), rpe=(8, 10), rest=75),
                exercise("overhead_triceps_ext", sets=3, reps=(10, 15), rpe=(8, 9), rest=75),
            ],
        ),
        day(
            "Pull B",
            exercises=[
                exercise("rdl", sets=4, reps=(5, 8), rpe=(7, 8), rest=180, progression="linear"),
                exercise(
                    "lat_pulldown",
                    sets=4,
                    reps=(8, 12),
                    rpe=(7, 9),
                    rest=120,
                    progression="double_progression",
                ),
                exercise("barbell_row", sets=3, reps=(8, 12), rpe=(7, 9), rest=120),
                exercise("leg_curl", sets=3, reps=(10, 15), rpe=(8, 9), rest=90),
                exercise("hammer_curl", sets=3, reps=(10, 15), rpe=(8, 9), rest=60),
                exercise("hanging_leg_raise", sets=3, reps=(10, 15), rpe=(8, 10), rest=60),
            ],
        ),
        day("Rest", is_rest_day=True),
        day("Rest", is_rest_day=True),
    ],
)
