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

### exercises
The hybrid library: curated core seeded from free-exercise-db plus user-contributed entries.
- `id`, `name`, `slug` unique
- `owner_id` nullable: null means curated, otherwise references user
- `primary_muscle` enum: chest, lats, traps, rhomboids, rear_delts, side_delts, front_delts, biceps, triceps, forearms, abs, obliques, lower_back, glutes, quads, hamstrings, adductors, abductors, calves
- `secondary_muscles` enum array
- `equipment` enum: barbell, dumbbell, cable, machine, bodyweight, banded, kettlebell, smith_machine, trap_bar, ez_bar, plate_loaded, cardio_machine, other
- `movement_pattern` enum: squat, hinge, horizontal_push, vertical_push, horizontal_pull, vertical_pull, lunge, carry, rotation, anti_rotation, isolation, cardio
- `tracking_type` enum: weight_reps, weight_reps_distance, weight_time, bodyweight_reps, weighted_bodyweight, time_only, distance_time, distance_time_pace, cardio_machine
- `notes`, `cues` text
- `is_unilateral` boolean

### programs
- `id`, `owner_id`, `name`, `description`, `goal` enum: hypertrophy, strength, powerbuilding, fat_loss, general, custom
- `weeks` int, `days_per_week` int
- `source` enum: template, manual, copied
- `template_id` nullable: references `program_templates.id` if copied from one

### program_days
- `id`, `program_id`, `day_index` (0..days_per_week-1), `name`

### program_day_exercises
- `id`, `program_day_id`, `exercise_id`, `position` int
- `target_sets` int
- `target_reps_low`, `target_reps_high` int nullable
- `target_rpe_low`, `target_rpe_high` numeric(3,1) nullable
- `target_rir_low`, `target_rir_high` int nullable
- `rest_seconds` int nullable
- `progression_strategy` enum: linear, double_progression, rpe_based, none
- `notes`

### scheduled_workouts
- `id`, `user_id`, `program_id` nullable, `program_day_id` nullable
- `scheduled_for` date, `status` enum: planned, in_progress, completed, skipped
- `mesocycle_week` int nullable, `is_deload` boolean default false

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

### sets
Single set, polymorphic by `tracking_type` of the parent exercise.
- `id`, `workout_exercise_id`, `set_index` int (0-based)
- `set_type` enum: working, warmup, drop, myo_rep, cluster, top_set, back_off, amrap
- `weight_kg` numeric(6,2) nullable
- `reps` int nullable
- `duration_seconds` int nullable
- `distance_meters` numeric(8,2) nullable
- `rpe` numeric(3,1) nullable
- `rir` int nullable
- `is_pr` boolean default false
- `notes`

### program_templates
Curated starter programs (PPL, UL, Arnold, 5/3/1, etc.).
- `id`, `slug` unique, `name`, `description`, `author`, `goal`, `weeks`, `days_per_week`
- `data` jsonb: full structure cloned into user `programs` on copy

## Progression and analytics tables

### muscle_volume_weekly
Materialized weekly per-user per-muscle metrics. Refreshed nightly.
- `id`, `user_id`, `iso_year`, `iso_week`, `muscle` enum, `working_sets` numeric, `tonnage_kg` numeric, `average_rir` numeric

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
- `id`, `source` enum: usda, off, custom, user
- `external_id` nullable (FDC ID for USDA, barcode for OFF)
- `name`, `brand` nullable, `serving_size_g` numeric, `serving_label` text
- `kcal_per_100g`, `protein_g_per_100g`, `carbs_g_per_100g`, `fat_g_per_100g`, `fiber_g_per_100g`
- `owner_id` nullable (custom user entries)

### meals
- `id`, `user_id`, `eaten_at` timestamptz, `meal_type` enum: breakfast, lunch, dinner, snack
- `notes`, `photo_url` nullable
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
