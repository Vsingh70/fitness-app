from seed.programs._dsl import day, exercise, program

SLUGS = {
    "squat": "barbell-squat",
    "bench": "barbell-bench-press-medium-grip",
    "deadlift": "barbell-deadlift",
    "ohp": "barbell-shoulder-press",
    "power_clean": "power-clean",
    "pull_up": "pullups",
}

template = program(
    slug="starting-strength-3day",
    name="Starting Strength (3-day)",
    description=(
        "Mark Rippetoe's novice linear progression. Add weight every workout. "
        "Three sessions per week, alternating A and B."
    ),
    author="Curated",
    goal="strength",
    weeks=12,
    days_per_week=3,
    slug_map=SLUGS,
    days=[
        day(
            "Day A",
            exercises=[
                exercise("squat", sets=3, reps=5, rpe=(7, 9), rest=240, progression="linear"),
                exercise("bench", sets=3, reps=5, rpe=(7, 9), rest=240, progression="linear"),
                exercise("deadlift", sets=1, reps=5, rpe=(8, 9), rest=300, progression="linear"),
            ],
        ),
        day(
            "Day B",
            exercises=[
                exercise("squat", sets=3, reps=5, rpe=(7, 9), rest=240, progression="linear"),
                exercise("ohp", sets=3, reps=5, rpe=(7, 9), rest=240, progression="linear"),
                exercise("power_clean", sets=5, reps=3, rpe=(7, 9), rest=180, progression="linear"),
            ],
        ),
        day(
            "Day A (alt)",
            exercises=[
                exercise("squat", sets=3, reps=5, rpe=(7, 9), rest=240, progression="linear"),
                exercise("bench", sets=3, reps=5, rpe=(7, 9), rest=240, progression="linear"),
                exercise(
                    "pull_up",
                    sets=3,
                    reps=(5, 10),
                    rpe=(7, 9),
                    rest=180,
                    progression="double_progression",
                    notes="Substitute chin-ups or assisted as needed; pull-ups optional but encouraged.",
                ),
            ],
        ),
    ],
)
