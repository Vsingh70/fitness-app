# 03.01 Program templates

## Context

Users build programs either from a template or from scratch. This task implements the template library and the "copy template into my programs" flow.

Reference: `00-overview/data-model.md` (programs, program_days, program_day_exercises, program_templates).

## Goal

Curated template library, browsing, and one-click copy into user programs.

## Templates to seed

Author at least these 8 templates, with full week-by-week structures:

1. PPL (6 day, hypertrophy)
2. Upper / Lower (4 day, hypertrophy)
3. Arnold split (6 day, hypertrophy)
4. Bro split (5 day, hypertrophy)
5. 5/3/1 BBB (4 day, strength + hypertrophy)
6. Starting Strength (3 day, strength, novice)
7. nSuns 5/3/1 LP (5 day, strength)
8. Push Pull (4 day, hypertrophy/general)

Each template:
- Full `program_templates.data` jsonb encoding weeks, days, exercises, sets, rep ranges, RPE/RIR targets, rest periods, progression strategy.
- A short description, goal tag, day count, weeks count.
- All exercise references resolve by slug to the seeded curated library.

Store templates as Python files under `apps/api/seed/programs/<slug>.py` for code review friendliness, plus a build step that ingests them on seed.

## Endpoints

- `GET /v1/program-templates` returns metadata (no full structure).
- `GET /v1/program-templates/{slug}` returns the full structure.
- `POST /v1/program-templates/{slug}/copy` creates a new `programs` row owned by the user with `source = 'template'` and `template_id = template.id`. Returns the full program.

## Deliverables

1. Migrations for `programs`, `program_days`, `program_day_exercises`, `program_templates`.
2. Models, schemas, routes.
3. Seed module that ingests all 8 template files.
4. A typed Python helper `apps/api/seed/programs/_dsl.py` to write templates ergonomically:
   ```python
   program(
       slug="ppl-6day",
       name="Push Pull Legs",
       goal="hypertrophy",
       weeks=8,
       days_per_week=6,
       days=[
           day("Push A", exercises=[
               exercise("bench-press", sets=4, reps=(6, 8), rpe=(7, 8), rest=180,
                        progression="double_progression"),
               ...
           ]),
           ...
       ],
   )
   ```
5. Tests: copy a template -> verify the resulting program is structurally identical to the template, with the user as owner.

## Acceptance criteria

- All 8 templates seed cleanly and resolve every exercise slug.
- Copying a template is atomic and creates the full nested structure.
- The seed is idempotent on slug.

## Dependencies

- `01.04 Exercise library`

## Out of scope

- AI-generated programs (not in chosen scope).
- Marketplace / community templates (not in scope).
