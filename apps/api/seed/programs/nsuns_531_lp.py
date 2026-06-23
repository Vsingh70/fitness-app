"""nSuns 5/3/1 LP, 5-day.

Volume-heavy auto-regulating linear progression off the 5/3/1 framework. The
per-week percentage tables are encoded in notes.
"""

from seed.programs._dsl import day, exercise, program

SLUGS = {
    "bench": "barbell-bench-press-medium-grip",
    "ohp": "barbell-shoulder-press",
    "squat": "barbell-squat",
    "deadlift": "barbell-deadlift",
    "close_grip_bench": "close-grip-barbell-bench-press",
    "incline_bench": "barbell-incline-bench-press-medium-grip",
    "front_squat": "front-barbell-squat",
    "barbell_row": "bent-over-barbell-row",
    "chin_up": "chin-up",
    "lat_pulldown": "wide-grip-lat-pulldown",
    "face_pull": "face-pull",
    "lateral_raise": "side-lateral-raise",
    "leg_curl": "lying-leg-curls",
}

T1_NOTES = (
    "nSuns T1: percent ladder of TM. Week 1: 65/75/85/85/85/80/75/70/65 across "
    "9 sets x 8/6/4/4/4/5/6/7/8+. Move up 2.5/5/10 kg on success."
)
T2_NOTES = "nSuns T2: 8 sets x 6/5/3/5/7/4/6/8 at 50/60/70/70/70/65/60/55%."

template = program(
    slug="nsuns-531-lp-5day",
    name="nSuns 5/3/1 LP (5-day)",
    description=(
        "Volume-rich linear progression off the 5/3/1 framework. Five days a "
        "week, two heavy compounds per day. Percentages in the notes."
    ),
    author="Curated",
    goal="strength",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Bench / OHP",
            exercises=[
                exercise(
                    "bench",
                    sets=9,
                    reps=(4, 8),
                    rpe=(7, 10),
                    rest=180,
                    progression="linear",
                    notes=T1_NOTES,
                ),
                exercise("ohp", sets=8, reps=(3, 8), rpe=(7, 10), rest=150, notes=T2_NOTES),
                exercise("chin_up", sets=4, reps=(6, 10), rpe=(8, 10), rest=90),
                exercise("face_pull", sets=3, reps=(15, 25), rpe=(8, 10), rest=60),
            ],
        ),
        day(
            "Squat / Sumo Deadlift",
            exercises=[
                exercise(
                    "squat",
                    sets=9,
                    reps=(4, 8),
                    rpe=(7, 10),
                    rest=240,
                    progression="linear",
                    notes=T1_NOTES,
                ),
                exercise(
                    "deadlift",
                    sets=8,
                    reps=(3, 6),
                    rpe=(7, 10),
                    rest=180,
                    notes="nSuns sumo deadlift T2. 50-70% TM.",
                ),
                exercise("leg_curl", sets=3, reps=(10, 15), rpe=(8, 10), rest=75),
            ],
        ),
        day(
            "OHP / Incline",
            exercises=[
                exercise(
                    "ohp",
                    sets=9,
                    reps=(4, 8),
                    rpe=(7, 10),
                    rest=180,
                    progression="linear",
                    notes=T1_NOTES,
                ),
                exercise(
                    "incline_bench", sets=8, reps=(3, 8), rpe=(7, 10), rest=150, notes=T2_NOTES
                ),
                exercise("barbell_row", sets=3, reps=(8, 12), rpe=(8, 10), rest=120),
                exercise("lateral_raise", sets=3, reps=(12, 20), rpe=(8, 10), rest=60),
            ],
        ),
        day(
            "Deadlift / Front Squat",
            exercises=[
                exercise(
                    "deadlift",
                    sets=9,
                    reps=(4, 8),
                    rpe=(7, 10),
                    rest=240,
                    progression="linear",
                    notes=T1_NOTES,
                ),
                exercise(
                    "front_squat",
                    sets=8,
                    reps=(3, 6),
                    rpe=(7, 10),
                    rest=180,
                    notes="Front squat T2. 50-70% TM.",
                ),
                exercise("leg_curl", sets=3, reps=(10, 15), rpe=(8, 10), rest=75),
            ],
        ),
        day(
            "Bench / Close-Grip",
            exercises=[
                exercise(
                    "bench",
                    sets=9,
                    reps=(4, 8),
                    rpe=(7, 10),
                    rest=180,
                    progression="linear",
                    notes=T1_NOTES,
                ),
                exercise(
                    "close_grip_bench", sets=8, reps=(3, 8), rpe=(7, 10), rest=150, notes=T2_NOTES
                ),
                exercise("lat_pulldown", sets=4, reps=(10, 15), rpe=(8, 10), rest=90),
                exercise("face_pull", sets=3, reps=(15, 25), rpe=(8, 10), rest=60),
            ],
        ),
        day("Rest", is_rest_day=True),
        day("Rest", is_rest_day=True),
    ],
)
