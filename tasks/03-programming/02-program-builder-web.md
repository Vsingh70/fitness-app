# 03.02 Program builder (web)

## Context

Manual program builder for users who don't want a template, plus editing for templates that were copied. Also: the catalog of seed templates and the "copy to my programs" UX.

## Goal

Browse templates, copy them, or build a program from scratch. Edit any user-owned program.

## Screens

### Programs list
Route: `/programs`. Two tabs:
- Mine: user's programs. Active one is pinned.
- Templates: browse the 8 seeded ones with filter chips (goal, days/week, level).

### Template detail
Route: `/programs/templates/[slug]`. Read-only preview of all weeks and days. Primary CTA "Use this program" calls the copy endpoint and redirects to the copied program.

### Program detail / editor
Route: `/programs/[id]`. Editable for user-owned programs.

Layout:
- Header: name, goal, weeks, days-per-week, an "Activate" button. Only one program can be active at a time per user (active is what drives `scheduled_workouts` generation).
- Tabs per week, then per day within the week.
- Day editor:
  - Reorderable list of `program_day_exercises`.
  - Each row: exercise, target sets, target rep range, target RPE/RIR, rest, progression strategy.
  - "Add exercise" button.
- Right rail: weekly volume summary per muscle (warns when a muscle is below 8 sets or above 22 sets per week, configurable per goal).

### Activate flow

Activating a program prompts:
- "Start on which date?"
- "Which day of the week is day 1?"
- Generates `scheduled_workouts` rows for the full duration.
- Old active program's future `scheduled_workouts` get marked `skipped` unless the user opts to keep them.

## API additions

- `POST /v1/programs` create empty program.
- `POST /v1/programs/{id}/days` add a day.
- `POST /v1/program-days/{id}/exercises` add an exercise to a day.
- `PATCH /v1/program-day-exercises/{id}` update targets.
- `POST /v1/programs/{id}/activate` body `{ start_date, weekday_offset }`. Generates scheduled workouts.
- `POST /v1/programs/{id}/deactivate`.

## Volume warnings

Compute weekly per-muscle set count from the program structure. Direct + indirect work counted with weights:
- Primary muscle of an exercise: 1.0 set
- Secondary muscle: 0.5 set

Show muscles outside `[8, 22]` weekly sets as a yellow warning per the goal. Settings page lets the user override the ideal range per muscle.

## Deliverables

1. API additions and migrations (if any) for activation logic.
2. Web routes and components.
3. Volume summary component shared with analytics later.
4. Tests for: activate generates the right number of scheduled workouts; deactivate handles overlap correctly.

## Acceptance criteria

- A user can build a 4-day program from scratch in under 5 minutes of UI work.
- Copying a template, tweaking exercises, and activating works end-to-end.
- Volume warnings update live as exercises change.

## Dependencies

- `03.01 Program templates`
- `01.05 Next.js web skeleton`

## Out of scope

- Calendar drag-and-drop rescheduling (separate small task later).
