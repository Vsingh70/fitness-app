# Data model

Authoritative reference for the Postgres schema. Tasks under `01-foundation`, `02-tracking`, etc. implement subsets of this. Update this file when the schema changes; do not let tasks drift.

## Conventions

- All tables have `id` (UUID v7, generated server-side), `created_at`, `updated_at` (UTC).
- Soft delete via `deleted_at` only where users can restore. Workout sessions, programs, meals: soft delete. Sets, foods consumed: hard delete.
- Foreign keys use `ON DELETE CASCADE` for owned children, `ON DELETE RESTRICT` for references to catalog data (exercises, foods).
- Money, weights, volumes stored as numeric with explicit units in column name (e.g. `weight_kg`, never just `weight`).
- All weights stored in kg internally. UI converts for display based on user preference.
- All distances stored in meters. All durations stored in seconds.
- Enums implemented as Postgres enums, not strings.

## Core tables

### users
- `id`, `email` unique, `display_name`, `apple_sub` nullable, `google_sub` nullable
- `unit_system` enum: metric, imperial
- `birthdate`, `sex_at_birth` enum: male, female, other (used for caloric/recovery defaults; never required)
- `timezone` IANA string
- `default_rest_seconds` int default 90: the user's preferred rest-timer default. Per-set resolution order is the program exercise's `rest_seconds` target, else the session's current default, else this user default.

### exercises
The hybrid library: curated core seeded from free-exercise-db plus user-contributed entries.
- `id`, `name`, `slug` unique
- `owner_id` nullable: null means curated, otherwise references user
- `primary_muscle` enum: chest, lats, traps, rhomboids, rear_delts, side_delts, front_delts, biceps, triceps, forearms, abs, obliques, lower_back, glutes, quads, hamstrings, adductors, abductors, calves
- `secondary_muscles` enum array
- `equipment` enum: barbell, dumbbell, cable, machine, bodyweight, banded, kettlebell, smith_machine, trap_bar, ez_bar, plate_loaded, cardio_machine, other
- `movement_pattern` enum: squat, hinge, horizontal_push, vertical_push, horizontal_pull, vertical_pull, lunge, carry, rotation, anti_rotation, isolation, cardio, mobility, plyometric (mobility/plyometric label drills so they stay out of strength analytics even if mis-blocked)
- `tracking_type` enum: weight_reps, weight_reps_distance, weight_time, bodyweight_reps, weighted_bodyweight, time_only, distance_time, distance_time_pace, cardio_machine
- `notes`, `cues` text
- `is_unilateral` boolean

### programs
A program is a single **microcycle** (an ordered list of training/rest slots, any length) repeated into a **mesocycle**. There is no weekday binding; advancement is pure rotation tracked per user in `program_progress`.
- `id`, `owner_id`, `name`, `description`, `goal` enum: hypertrophy, strength, powerbuilding, fat_loss, general, custom
- `microcycle_length` int: number of slots in the microcycle. Recomputed server-side from the slot count; never trust a client value.
- `mesocycle_length_microcycles` int (default 4): how many repetitions of the microcycle make one mesocycle, before an optional deload microcycle.
- `source` enum: template, manual, copied
- `template_id` nullable: references `program_templates.id` if copied from one
- `is_active` boolean, `activated_at` nullable
- `auto_deload` boolean (default true): when true, a deload microcycle is appended after the last repetition of each mesocycle
- `periodization_mode` enum: retained, gates deload behavior; no longer drives a pre-generated calendar
- `auto_deload_on_stall` boolean, `intensity_mode` enum: rpe, rir, percent
- `deleted_at` nullable (soft delete)

### program_days
A **slot** in the microcycle. May be a training slot or a rest slot.
- `id`, `program_id`, `slot_index` (0-based position within the microcycle), `name`
- `is_rest_day` boolean (default false): rest slots carry no exercises in the rotation; existing exercise rows are hidden, not deleted, when a training slot is toggled to rest (they reappear if toggled back)

### program_day_exercises
- `id`, `program_day_id`, `exercise_id`, `position` int
- `target_sets` int
- `target_reps_low`, `target_reps_high` int nullable
- `target_rpe_low`, `target_rpe_high` numeric(3,1) nullable
- `target_rir_low`, `target_rir_high` int nullable
- `rest_seconds` int nullable
- `progression_strategy` enum: linear, double_progression, rpe_based, none
- `notes`
- `block_kind` enum: warmup, working, cooldown — NOT NULL, default `working`; copied onto the materialized `workout_exercise` when a session is started from the program (so cooldown/mobility slots are excluded from working-volume and PR analytics)
- `block_label` text nullable — optional display label (e.g. "Mobility Circuit"), also carried into the session

### scheduled_workouts
Retained but demoted: the calendar is projected from the rotation (`program_progress` + slots) rather than pre-generated. Rows are written on session start/skip for history.
- `id`, `user_id`, `program_id` nullable, `program_day_id` nullable
- `scheduled_for` date **nullable**, `status` enum: planned, in_progress, completed, skipped
- `microcycle_number` int nullable, `repetition` int nullable (replace the old `mesocycle_week`)
- `is_deload` boolean default false

### program_progress
Per-user-per-program rotation position. Unique on (`user_id`, `program_id`).
- `id`, `user_id`, `program_id`
- `current_slot_index` int (default 0), `current_microcycle_number` int (default 1), `current_repetition` int (default 1)
- `in_deload` boolean (default false): true while the appended deload microcycle is in progress
- `last_completed_at` timestamptz nullable: set when a slot is advanced via completion (not skip)
- Advanced by the rotation engine (`POST /programs/{id}/advance`): within a microcycle `slot_index += 1`; at microcycle end the repetition bumps, then a deload microcycle (when `auto_deload`) or the next mesocycle starts.

### workout_sessions
The actual logged workout. May or may not reference a scheduled_workout.
- `id`, `user_id`, `scheduled_workout_id` nullable
- `name`, `started_at`, `ended_at` nullable
- `notes`, `bodyweight_kg` nullable
- `perceived_exertion` int 1-10 nullable
- `deleted_at` nullable

### workout_exercises
One per exercise per session.
- `id`, `workout_session_id`, `exercise_id`, `position` int, `notes`
- `block_kind` enum `block_kind`: warmup, working, cooldown (default `working`). Block grouping for warm-up/cooldown *routines of varied movements*. **Only `working` blocks count** toward working-volume rollups, per-muscle analytics, and PR detection; warm-up/cooldown blocks are logged and visible in history but never counted as training volume.
- `block_label` text nullable (e.g. "Mobility")
- `substituted_for_exercise_id` uuid nullable → exercises: set on a temporary one-session swap. The row's `exercise_id` becomes the substitute (logged sets credit it); the recorded original **pauses** — it is neither progressed nor stalled and is ignored by analytics for this slot.

### sets
Single set, polymorphic by `tracking_type` of the parent exercise.
- `id`, `workout_exercise_id`, `set_index` int (0-based)
- `set_type` enum: working, warmup, drop, myo_rep, cluster, top_set, back_off, amrap, interval
- `weight_kg` numeric(6,2) nullable
- `reps` int nullable
- `duration_seconds` int nullable
- `distance_meters` numeric(8,2) nullable
- `rpe` numeric(3,1) nullable
- `rir` int nullable
- `rounds` int nullable: interval/HIIT round count (`set_type=interval`); one round is described by this set's `work`/`rest` segments
- `is_pr` boolean default false
- `notes`
- A "working set" for analytics = any non-`warmup` set type. Ramp-up `warmup` sets of the same lift are excluded; structured efforts (drop/myo_rep/cluster/top_set/back_off/amrap/interval) count.

### set_segments
Intra-set sub-bouts: rest-pause/cluster/myo `mini_set` bouts, or interval `work`/`rest` segments. A plain straight set has zero segments (the `sets` row carries the values).
- `id`, `set_id` → sets (CASCADE), `segment_index` int (unique per set)
- `kind` enum `segment_kind`: work, rest, mini_set
- `reps`, `weight_kg` numeric(6,2), `duration_seconds`, `distance_meters` numeric(8,2), `rest_seconds` — all nullable
- **Segment-summed reps:** a rest-pause/cluster set's total reps for tonnage and PR e1RM = sum of its `mini_set` segment reps (a 10+3+2 counts as 15), falling back to the set's own `reps` for plain sets.
- **Intervals:** work time and distance come from `work` segments only; `rest` segments are excluded from work volume.

### program_templates
Curated starter programs (PPL, UL, Arnold, 5/3/1, etc.) plus user-saved templates.
- `id`, `slug` unique, `name`, `description`, `author`, `goal`
- `microcycle_length` int, `mesocycle_length_microcycles` int (default 4)
- `owner_id` nullable: null means curated; otherwise references the user who saved it
- `visibility` enum nullable `template_visibility`: private, shared (null for curated templates). List visibility = curated (`owner_id IS NULL`) + the requester's own + all `shared`.
- `data` jsonb: full structure cloned into user `programs` on copy, in the slots shape
  `{"slug_map": {"<key>": "<exercise-slug>", ...}, "slots": [{"name", "is_rest_day", "exercises": [...]}]}`

## Progression and analytics tables

### muscle_volume_weekly
Materialized weekly per-user per-muscle metrics. Refreshed nightly.
- `id`, `user_id`, `iso_year`, `iso_week`, `muscle` enum, `working_sets` numeric, `tonnage_kg` numeric, `average_rir` numeric
- Counting rules (shared by volume rollups, per-muscle analytics, PR detection, strength/stagnation insights):
  - Only `working` blocks (`workout_exercises.block_kind = 'working'`) count; warm-up/cooldown blocks are excluded.
  - Only non-`warmup` set types count; ramp-up warm-up sets of the same lift are excluded.
  - Structured-set reps are segment-summed: a rest-pause/cluster `mini_set` total (10+3+2 → 15) drives tonnage and PR e1RM.
  - Skipped sessions (linked `scheduled_workouts.status = 'skipped'`) and substituted-for originals are ignored.

### exercise_progression
Per-user-per-exercise rolling state for the progression engine.
- `id`, `user_id`, `exercise_id` (unique together)
- `current_top_set_weight_kg`, `current_target_reps`, `current_target_rpe`
- `consecutive_successes`, `consecutive_failures`
- `last_updated_at`

### recommendations
What the engine suggests for next session, kept until consumed.
- `id`, `user_id`, `scheduled_workout_id` nullable, `exercise_id`
- `kind` enum: increase_weight, increase_reps, hold, deload, swap, add_set, remove_set
- `payload` jsonb
- `rationale` text (LLM-generated explanation)
- `consumed_at` nullable

### analytics_insights
Strong/weak point and stagnation findings.
- `id`, `user_id`, `kind` enum: weak_muscle, strong_muscle, stagnation, imbalance, undertrained
- `subject` text (muscle or exercise slug)
- `severity` enum: info, warn, action
- `payload` jsonb, `rationale` text
- `surfaced_at`, `dismissed_at` nullable

## Nutrition tables

### foods
- `id`, `source` enum: usda, off, custom, user (a dormant `fatsecret` value lingers in the Postgres enum from migration 0021 but is unused — FatSecret was removed before launch; Postgres has no DROP VALUE)
- `external_id` nullable (FDC ID for USDA generic foods; GTIN/UPC for USDA Branded and OFF barcodes)
- `name`, `brand` nullable, `serving_size_g` numeric, `serving_label` text
- `kcal_per_100g`, `protein_g_per_100g`, `carbs_g_per_100g`, `fat_g_per_100g`, `fiber_g_per_100g`
- `owner_id` nullable (custom user entries)
- `payload` jsonb: USDA rows carry `category` (`foundation_food`/`sr_legacy_food`/`branded_food`) so search ranks clean generic foods first; branded barcode rows carry `fdc_id`
- Data is self-hosted: bulk-ingested from USDA FoodData Central (Foundation, SR Legacy, Branded) and the Open Food Facts nightly dump via `apps/api/scripts/ingest/` (idempotent UPSERT on `(source, external_id)`). Search uses the `pg_trgm` GIN index on `name`; barcode resolves locally with a live OFF fallback that caches. Refresh runbook: `docs/runbooks/food-data-refresh.md`. No paid food-data provider.

### food_servings
- `id`, `food_id` FK -> foods (ON DELETE CASCADE), `description`, `metric_amount` numeric, `metric_unit` enum: g, ml, `grams` numeric (resolved gram weight), `is_default` bool
- Named servings (e.g. "1 cup", "100 g") so meal entry can convert any selection back to grams; per-100g macros on `foods` stay the canonical math base

### meals
- `id`, `user_id`, `eaten_at` timestamptz, `meal_type` enum: breakfast, lunch, dinner, snack
- `notes` nullable
- `deleted_at`

### meal_items
- `id`, `meal_id`, `food_id`, `grams` numeric
- `kcal`, `protein_g`, `carbs_g`, `fat_g` denormalized at insert (so historical edits to food row don't rewrite history)

### meal_plans
- `id`, `user_id`, `name`, `target_kcal`, `target_protein_g`, `target_carbs_g`, `target_fat_g`
- `days` jsonb (structured plan)

## Fitbit tables

### fitbit_connections
- `id`, `user_id` unique, `access_token_encrypted`, `refresh_token_encrypted`
- `expires_at`, `scopes` text array, `fitbit_user_id`

### fitbit_activities
Imported workouts and activities from Fitbit.
- `id`, `user_id`, `fitbit_log_id` unique
- `activity_type`, `started_at`, `duration_seconds`, `calories`
- `average_hr`, `max_hr`, `steps`, `distance_meters`
- `raw` jsonb

### daily_metrics
Daily aggregates from Fitbit (steps, HR, sleep, RHR).
- `id`, `user_id`, `date`, `steps`, `resting_hr`, `hrv_ms`, `sleep_minutes`, `sleep_score`, `readiness_score`

## Indexes

- `workout_sessions(user_id, started_at desc)`
- `sets(workout_exercise_id, set_index)`
- `meals(user_id, eaten_at desc)`
- `daily_metrics(user_id, date desc)`
- `foods` GIN index on `name` (pg_trgm) for fuzzy search
- `exercises` GIN index on `name`

## Migrations

Alembic, one migration per merged PR that touches the schema. Never edit historical migrations.
