# Active-Session Logging + Structured Work (06 + 05)

> Implements `tasks/redesign/06-workout-session.md` (core logging loop, structured work, freestyle,
> adjustable rest) and `tasks/redesign/05-active-session.md` (in-session swap / permanent edit / skip).
> Phase 1 (this workflow) = backend, additive migration `0028`. Phase 2 = web logging UI. Built by the
> loop (Builder = `api-dev`/`web-dev`, Checker = `qa-verifier`).

The schema is **additive** — new table + nullable/defaulted columns + enum extensions — so the full
test suite stays green at every task (no red valley).

## Phase 1 — backend (this workflow)

### Task A — migration 0028 + models (additive)
Per `06 §7`. Read the current `app/models/workout.py` (WorkoutSession/WorkoutExercise/WorkoutSet),
`app/models/exercise.py`, `app/models/user*.py`, and the `SetType`/`MovementPattern` enums; follow the
0027 migration style.
- New table **`set_segments`**: `id`, `set_id` FK→workout_sets CASCADE, `segment_index`, `kind` enum
  `segment_kind` (`work`/`rest`/`mini_set`), nullable `reps`, `weight_kg`, `duration_seconds`,
  `distance_meters`, `rest_seconds`.
- New columns: `workout_sets.rounds` (nullable int), `workout_exercises.block_kind` enum `block_kind`
  (`warmup`/`working`/`cooldown`, default `working`) + `workout_exercises.block_label` (nullable),
  `users.default_rest_seconds` (int, default 90).
- Enum extensions: `set_type` gains `interval` (keep existing values incl. any myo_rep/cluster/warmup);
  exercise categorization gains `mobility` + `plyometric` — extend `movement_pattern` OR add a new
  `exercise.category` column (pick whichever is least disruptive; prefer extending `movement_pattern`
  if the enum already carries similar values, else add `category` nullable).
- ORM models for all the above + a `SetSegment` model registered in metadata.
- **DoD:** `alembic upgrade head` + down/up round-trip; `pytest -q` green; ruff clean.

### Task B — schemas + endpoints + rotation wiring
Per `06 §1,§4,§5` and `05`.
- Schemas + endpoints for: creating a set with `set_segments` (rest-pause/cluster/myo via `mini_set`
  segments), interval sets (`set_type=interval`, `rounds`, work/rest segments); setting
  `workout_exercises.block_kind`/`block_label`; a `users.default_rest_seconds` preference
  (GET/PATCH on the user/me) and the per-session rest override is client-side/session-state.
- **Finish advances rotation** (`06 §1`): when a session linked to a program slot is finished, advance
  the program rotation (`app/services/rotation.advance` via the program-progress service) — completing
  consumes the slot. Freestyle sessions (no scheduled link) do NOT advance.
- **Skip** (`05 §4`): a `POST .../skip` that marks the session/scheduled status `skipped`, advances the
  rotation neutrally (`advance_position(..., as_skip=True)`), and is ignored by progression.
- **Temp swap** (`05 §2`): set `workout_exercises.substituted_for_exercise_id` (add this nullable column
  in Task A if not present) so the original pauses (not stalls); logged sets count to the substitute.
- **Permanent edit** (`05 §3`): reuse the program slot-exercise endpoints (already exist).
- Add tests for: segment-summed reps, interval rounds, block_kind, rest default, finish-advances-rotation,
  skip-advances-neutrally, temp-swap link.
- **DoD:** `pytest -q` green; ruff clean.

### Task C — analytics + OpenAPI
Per `06 §6`.
- Working-volume rollups, per-muscle analytics, and PR detection count **only `working` blocks**;
  rest-pause/cluster total reps = sum of segment reps; interval work time/distance from work segments
  (rest segments excluded); warm-up/cooldown never counted; substituted-for originals + skipped sessions
  ignored. Update the rollup/analytics services + their tests.
- Update `tasks/00-overview/data-model.md`; regenerate `packages/openapi/openapi.json`
  (`uv run python scripts/export_openapi.py`) + web types (`pnpm openapi:generate`).
- **DoD:** `pytest -q` green; ruff clean; OpenAPI no-drift.

## Phase 2 — web logging UI (next workflow, after Phase 1)
Per `06 §1,§2,§3` + `05`. The set-row variants, exercise card, rest bar already exist
(`src/components/workouts/*`); add structured-work UI (segment editor for rest-pause/cluster, interval
timer driving rounds, warm-up/cooldown block grouping), the adjustable rest control (session default +
"save as my default"), freestyle start, and the in-session **Swap / Change in program / Skip** actions
wired to the Phase-1 endpoints. Offline-first per the design brief (no mid-session blocking).

## Out of scope
- iOS logging UI (catches up after the web shape settles).
- Progression-engine formulas (this defines inputs/what-counts, not the math).
