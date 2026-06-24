# Workout session: the core logging loop

The ground-up spec for logging a workout. This is the core that `05-active-session.md`
(in-session swap, edit, skip) extends and that the program rotation in
`01-program-model.md` feeds. Full stack. It resolves the structured-work and freestyle
questions that the earlier passes left open.

Read `05` alongside this: `06` is the loop, `05` is what happens when the loop diverges
from the program.

## 0. Decisions locked

- Structured work is **first-class**: rest-pause and cluster sub-bouts, interval/HIIT
  rounds, and warm-up blocks of varied movements all get real schema, not flags on
  repeated rows.
- Freestyle (no-program) workouts are **first-class**: a session can start empty with no
  program, and per-exercise progression still tracks.
- The default rest timer is **adjustable mid-workout**.

## 1. The loop (happy path)

1. **Start.** Two origins, both first-class:
   - From a program: Today or Workouts starts the current rotation slot
     (`01-program-model.md`), pre-filling exercises and targets.
   - Freestyle: "Start empty workout" creates a session with no `scheduled_workout`
     link; the user adds exercises as they go.
2. **Log.** Per exercise, a card with set rows. The set-row layout is driven by the
   exercise `tracking_type` (six variants already shipped). A logged set auto-starts the
   rest timer.
3. **Rest.** The floating rest bar counts down from the active rest value (section 4).
4. **Finish.** Ends the session, runs PR detection, routes to the summary.
5. **Summary.** PRs, volume by muscle (working sets only), set-by-set table, notes, and
   next-session recommendations. Completing advances the rotation pointer when the
   session came from a program.

Offline is non-negotiable (design brief section 7): logging a set never blocks on the
network. Sets save locally and sync in the background; each set shows a quiet
synced/pending badge, never a mid-session modal.

## 2. Inherited mechanics (keep)

These exist in `apps/web/src/components/workouts/` and carry forward unchanged unless a
section below modifies them: exercise card, set row (six tracking-type variants), rest
timer and floating rest bar, session timer, sticky bottom bar, plate math, keyboard
shortcuts, next-up preview, exercise picker, read-only session view. The redesign adds
structure around them, it does not rewrite the set row.

## 3. Structured work (new schema)

Three structures, two new mechanisms.

### 3a. Intra-set sub-bouts: rest-pause, cluster, myo-rep

A set like 10+3+2 is one logical effort made of several bouts. Add a child table:

- **`set_segments`**: `id`, `set_id`, `segment_index`, `kind` enum
  (`work`, `rest`, `mini_set`), `reps?`, `weight_kg?`, `duration_seconds?`,
  `distance_meters?`, `rest_seconds?`.
- A normal straight set has zero segments (the `sets` row carries the values, as today).
  A rest-pause/cluster set marks `set_type` (`myo_rep`, `cluster`) and stores its bouts
  as `mini_set` segments; total reps for analytics is the sum of segment reps.

### 3b. Interval / HIIT rounds

Intervals reuse the same segment mechanism so there is one concept, not two:

- An interval set marks a new `set_type = interval`, with `rounds` count on the set, and
  `work`/`rest` segments describing one round (for example work 30s, rest 15s). Analytics
  read work time and distance across rounds; rest segments are excluded from work volume.
- An interval timer in the UI drives the work/rest countdown automatically for the round
  count. This replaces logging each interval as a disconnected `time_only` row.

### 3c. Warm-up and cooldown blocks of varied movements

A warm-up made of different stretches/mobility drills is not warm-up *sets* of a working
lift; it is its own group of movements. Add a block grouping above the exercise:

- **`workout_exercises.block_kind`** enum (`warmup`, `working`, `cooldown`), default
  `working`, plus optional `block_label` (for example "Mobility").
- Working-volume rollups, per-muscle analytics, and PR detection consider **only
  `working` blocks**. Warm-up and cooldown movements are logged and visible in history
  but never counted as training volume.
- Exercise categorization: extend the exercise `movement_pattern` (or add a `category`)
  to include `mobility`/`stretch` so these movements are labeled and kept out of strength
  analytics even if mis-blocked. Plyometrics get a `plyometric` label for the same reason.

`set_type = warmup` still works for warm-up sets *of the same working lift* (ramp-up sets
of bench). The block handles warm-up *routines of other movements*. Both coexist.

## 4. Adjustable rest timer

Replace the hardcoded `DEFAULT_REST_SECONDS = 90` in the active-session page.

- Add **`users.default_rest_seconds`** (preference, seeded at 90).
- The active rest value for a given set resolves in order: the program exercise's
  `rest_seconds` target if set, else the session's current default, else the user default.
- Mid-workout, the rest bar exposes a control to change the **session default**. The new
  value applies to every subsequent rest in the session. An optional "Save as my default"
  writes it to `users.default_rest_seconds`.
- Honors reduced motion and stays reachable one-handed (bottom 60 percent of the screen).

## 5. Freestyle (no-program) sessions

- `workout_sessions.scheduled_workout_id` is already nullable; the freestyle path uses it.
  Confirm and keep.
- A freestyle session supports the full logging experience (not a stripped quick-log):
  add any exercise, all set types and structures from section 3, the rest timer, the
  summary.
- Per-exercise progression state (`exercise_progression`) updates from freestyle work the
  same as programmed work, so a one-off still moves the lift's numbers.
- Freestyle sessions do not touch the rotation pointer (there is no slot to advance).

## 6. Progression and analytics impact

- **Working volume** counts only `working` blocks; warm-up and cooldown are excluded.
- **Rest-pause/cluster** total reps come from summed segments, so a 10+3+2 counts as 15
  reps at the logged load, not 10.
- **Intervals** contribute work time and distance per round; rest segments are excluded.
- **PRs** are detected on working sets only (a warm-up single is never a PR).
- Substituted-for originals and skipped sessions are ignored per `05-active-session.md`.

## 7. Schema summary (migration)

One migration after the program-model one. Additive where possible:

- New table `set_segments` (section 3a/3b).
- New columns: `sets`-level `rounds` (nullable, interval sets), `workout_exercises.block_kind`
  enum + `block_label`, `users.default_rest_seconds`.
- Enum extensions: `set_type` gains `interval`; exercise categorization gains `mobility`
  and `plyometric` (on `movement_pattern` or a new `category`).
- Update `00-overview/data-model.md` and regenerate OpenAPI + web types.

## 8. Acceptance

- [ ] A session starts from a program slot or as a freestyle empty session, both with the
      full logging experience.
- [ ] Rest-pause/cluster sets store sub-bouts; total reps sum the segments.
- [ ] Interval sets store rounds with work/rest segments and an interval timer drives them.
- [ ] A warm-up block of varied movements is logged separately and excluded from working
      volume and PRs.
- [ ] The rest timer default is adjustable mid-workout and optionally savable as the user
      default.
- [ ] Logging works fully offline with per-set sync badges, no mid-session blocking.
- [ ] Working volume, PRs, and per-muscle analytics count only working blocks and sum
      structured-set reps correctly.
- [ ] data-model.md updated; migration applied; OpenAPI and web types regenerated; tests
      pass.

## 9. Out of scope

- Progression-engine formulas (this defines the inputs and what counts, not the math).
- iOS implementation (catches up after the web shape settles).
- Restaurant/recipe data (nutrition, see `07-nutrition.md`).
