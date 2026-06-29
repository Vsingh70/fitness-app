from seed.programs._dsl import day, exercise, program

SLUGS = {
    "cycling": "cycling",
}

template = program(
    slug="cycling-endurance",
    name="Cycling Endurance",
    description=(
        "A polarized cycling week: lots of zone-2 endurance, one threshold "
        "interval day, a tempo/sweet-spot ride, and a long weekend ride. Works on "
        "the road or a trainer."
    ),
    author="Curated",
    goal="endurance",
    mesocycle_length_microcycles=4,
    slug_map=SLUGS,
    days=[
        day(
            "Endurance Ride",
            exercises=[
                exercise(
                    "cycling",
                    sets=1,
                    rpe=(5, 6),
                    rest=0,
                    notes="60–90 min steady aerobic (Zone 2); smooth, sustainable effort.",
                )
            ],
        ),
        day(
            "Recovery Spin",
            exercises=[
                exercise(
                    "cycling",
                    sets=1,
                    rpe=(3, 4),
                    rest=0,
                    notes="30–40 min very easy, high cadence, flat terrain.",
                )
            ],
        ),
        day(
            "Threshold Intervals",
            exercises=[
                exercise(
                    "cycling",
                    sets=4,
                    rpe=(8, 9),
                    rest=300,
                    notes="4 × 8 min at threshold, 5 min easy spin between.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
        day(
            "Tempo Ride",
            exercises=[
                exercise(
                    "cycling",
                    sets=1,
                    rpe=(6, 7),
                    rest=0,
                    notes="45–60 min at tempo / sweet-spot effort.",
                )
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
                    notes="2–3 hr endurance; fuel and drink every ~45 min.",
                )
            ],
        ),
        day("Rest", is_rest_day=True),
    ],
)
