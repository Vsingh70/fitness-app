"""5/3/1 BBB (Boring But Big), 4-day.

Percentages are encoded in the per-exercise `notes` field since the schema
stores absolute targets. See clarifying-Q decision in task 03.01.
"""

from seed.programs._dsl import day, exercise, program

SLUGS = {
    "ohp": "barbell-shoulder-press",
    "deadlift": "barbell-deadlift",
    "bench": "barbell-bench-press-medium-grip",
    "squat": "barbell-squat",
    "pull_up": "pullups",
    "barbell_row": "bent-over-barbell-row",
    "dips": "dips-triceps-version",
    "barbell_curl": "barbell-curl",
    "leg_curl": "lying-leg-curls",
    "hanging_leg_raise": "hanging-leg-raise",
}

BBB_NOTE_MAIN = (
    "5/3/1 main lift. Week 1: 65/75/85% x 5/5/5+. Week 2: 70/80/90% x 3/3/3+. "
    "Week 3: 75/85/95% x 5/3/1+. Week 4 deload: 40/50/60% x 5/5/5. Percentages "
    "are of your Training Max (90% of 1RM)."
)
BBB_NOTE_BBB = "Boring But Big supplemental: 5 sets of 10 at 50-60% of TM."

template = program(
    slug="531-bbb-4day",
    name="5/3/1 BBB (4-day)",
    description=(
        "Jim Wendler's 5/3/1 with Boring But Big supplemental sets. Strength + "
        "hypertrophy, four lifts as anchors. Reps/percent in the notes column."
    ),
    author="Curated",
    goal="powerbuilding",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "OHP day",
            exercises=[
                exercise(
                    "ohp",
                    sets=3,
                    reps=(1, 5),
                    rpe=(8, 10),
                    rest=240,
                    progression="rpe_based",
                    notes=BBB_NOTE_MAIN,
                ),
                exercise("ohp", sets=5, reps=10, rest=120, notes=BBB_NOTE_BBB),
                exercise("pull_up", sets=5, reps=(8, 12), rpe=(7, 9), rest=90),
                exercise("barbell_curl", sets=3, reps=(10, 15), rpe=(8, 9), rest=75),
            ],
        ),
        day(
            "Deadlift day",
            exercises=[
                exercise(
                    "deadlift",
                    sets=3,
                    reps=(1, 5),
                    rpe=(8, 10),
                    rest=300,
                    progression="rpe_based",
                    notes=BBB_NOTE_MAIN,
                ),
                exercise("deadlift", sets=5, reps=10, rest=180, notes=BBB_NOTE_BBB),
                exercise("leg_curl", sets=5, reps=(10, 15), rpe=(8, 9), rest=75),
                exercise("hanging_leg_raise", sets=3, reps=(10, 15), rpe=(8, 10), rest=60),
            ],
        ),
        day(
            "Bench day",
            exercises=[
                exercise(
                    "bench",
                    sets=3,
                    reps=(1, 5),
                    rpe=(8, 10),
                    rest=240,
                    progression="rpe_based",
                    notes=BBB_NOTE_MAIN,
                ),
                exercise("bench", sets=5, reps=10, rest=120, notes=BBB_NOTE_BBB),
                exercise("barbell_row", sets=5, reps=(8, 12), rpe=(7, 9), rest=120),
                exercise("dips", sets=5, reps=(8, 15), rpe=(8, 10), rest=90),
            ],
        ),
        day(
            "Squat day",
            exercises=[
                exercise(
                    "squat",
                    sets=3,
                    reps=(1, 5),
                    rpe=(8, 10),
                    rest=300,
                    progression="rpe_based",
                    notes=BBB_NOTE_MAIN,
                ),
                exercise("squat", sets=5, reps=10, rest=180, notes=BBB_NOTE_BBB),
                exercise("leg_curl", sets=5, reps=(10, 15), rpe=(8, 9), rest=75),
                exercise("hanging_leg_raise", sets=3, reps=(10, 15), rpe=(8, 10), rest=60),
            ],
        ),
    ],
)
