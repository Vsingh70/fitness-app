# 01.04 Exercise library

## Context

The exercise catalog is hybrid: a curated core seeded from `free-exercise-db` plus user-contributed entries. Every downstream feature (logging, programming, analytics) depends on this.

Reference: `00-overview/data-model.md` (exercises table).

## Goal

Seed a clean curated exercise catalog and expose endpoints to read it and add user-owned custom exercises.

## Seed data

1. Pull `free-exercise-db` (https://github.com/yuhonas/free-exercise-db) into `apps/api/seed/`.
2. Write a one-shot seed script `apps/api/scripts/seed_exercises.py` that:
   - Reads the JSON.
   - Maps fields to our schema. The source has `primaryMuscles`, `secondaryMuscles`, `equipment`, `category`. Map carefully; do not invent.
   - Filters to ~300 high-quality entries. Drop oddities (yoga poses, BJJ moves, etc.). Keep barbell/dumbbell/cable/machine/bodyweight strength + standard cardio modalities.
   - Assigns each exercise a `tracking_type` based on category + equipment (see data-model for the enum).
   - Sets `owner_id` to NULL (curated).
   - Generates a stable `slug` from `name` (kebab case, deduped).
3. Re-running the script is idempotent: upsert by slug.

## Endpoints

- `GET /v1/exercises`
  - Query params: `q` (fuzzy search using pg_trgm), `muscle`, `equipment`, `movement_pattern`, `tracking_type`, `mine_only` boolean.
  - Cursor pagination.
  - Returns curated + user's own custom exercises.
- `GET /v1/exercises/{id}`
- `POST /v1/exercises` (authenticated)
  - Creates a user-owned custom exercise. `owner_id` = current user.
  - Validate the same fields as curated entries.
- `PATCH /v1/exercises/{id}` (authenticated)
  - Only allowed if `owner_id` matches current user.
- `DELETE /v1/exercises/{id}` (authenticated)
  - Only allowed if `owner_id` matches current user AND the exercise is not referenced by any of the user's workouts. Otherwise return 409 with a clear message; suggest archiving (`archived_at` column to add now).

## Schema additions

Add `archived_at` nullable timestamptz to `exercises`. When set, the exercise no longer shows in default search but still resolves by id.

## Deliverables

1. Alembic migration for `exercises` table (full schema per data-model) + `archived_at`.
2. SQLAlchemy model + Pydantic schemas.
3. Seed script + the upstream data committed under `seed/exercises/`.
4. Routes + service layer.
5. Tests:
   - Seed produces ~300 rows on a clean db.
   - Re-running seed is a no-op.
   - User can create, edit, archive their custom exercise.
   - User cannot edit or delete a curated exercise.
   - Search returns expected hits for `bench`, `squat`, `row`, `db curl`.

## Acceptance criteria

- After running the seed, `GET /v1/exercises?q=bench` returns at least flat bench, incline bench, dumbbell bench variants.
- Searching by muscle returns only exercises that target it primary or secondary.
- Custom exercise creation and archive work via the API.

## Dependencies

- `01.02 FastAPI skeleton`
- `01.03 Auth`

## Out of scope

- Exercise demonstration videos or images (later phase).
- Equipment availability filtering per gym (not in v1).
