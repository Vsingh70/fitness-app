# Program model: flexible microcycle and mesocycle

Full-stack spec. This replaces the rigid `days_per_week` / `weeks` model in
`programs`, `program_days`, `program_templates`, and `scheduled_workouts`. It is
the gate for the Programs UI in `02-programs-screens.md`.

## 1. Concepts

- **Slot**: one position in a microcycle. Either a training day or a rest day.
- **Microcycle**: an ordered list of slots. Its length is the slot count. It can
  be any length (4, 7, 8, whatever the user builds). It is not tied to a 7-day week.
- **Mesocycle**: the microcycle repeated N times, where N is set when the user
  picks periodization. An optional deload microcycle is appended after the N
  repetitions and is tracked separately, not counted in N.
- **Rotation, not calendar**: progress is a position in the rotation, advanced when
  the user trains. There is no assumption that slot index maps to a weekday or date.

Worked example. A program with an 8-slot microcycle
(`Push / Pull / Legs / Rest / Push / Pull / Legs / Rest`), mesocycle length 4, and
auto-deload on: the user trains 6 sessions per microcycle, the microcycle repeats 4
times, then a single deload microcycle runs, then the engine rolls into the next
mesocycle.

## 2. Schema changes

Update `00-overview/data-model.md` to match as part of this task.

### programs

Remove the weekly framing, add the cycle framing.

- Remove `days_per_week`. Remove `weeks`.
- Add `microcycle_length` int. Derived from the slot count, persisted so the engine
  and analytics do not recompute it. Validated to equal the number of `program_days`
  rows on save.
- Rename `mesocycle_length_weeks` to `mesocycle_length_microcycles` int. This is the
  N the user sets when choosing periodization. Minimum 1.
- Keep `auto_deload` bool. When true, a deload microcycle is appended after the N
  repetitions. Keep `auto_deload_on_stall` as is.
- Keep `periodization_mode`, `intensity_mode`, `goal`, `source`, `template_id`,
  `is_active`, `activated_at`, `deleted_at`.

### program_days  (now microcycle slots)

This table is now an ordered list of slots, not weekday-bound days.

- Rename `day_index` to `slot_index` (0-based, 0..microcycle_length-1).
- Add `is_rest_day` bool, default false. When true, the slot has no exercises and
  `name` is optional (defaults to "Rest").
- Keep `name`, `program_id`. Keep the ordering by `slot_index`.
- `program_day_exercises` is unchanged in shape and still hangs off training slots.
  Rest slots have zero exercise rows.

### program_templates

- Replace `weeks` and `days_per_week` with `microcycle_length` and
  `mesocycle_length_microcycles`.
- The `data` jsonb gains a `slots` array (each slot `{ name, is_rest_day, exercises }`)
  in place of any weekday-shaped structure. Update the seed templates accordingly.
- Add `owner_id` nullable: null means a curated template (the seeded set); non-null
  means a user saved one of their programs as a template (see section 4).
- Add `visibility` enum: `private`, `shared`. Only meaningful when `owner_id` is set.
  `private` is visible only to the owner; `shared` is visible to all users (the small
  group of training partners). Curated templates behave as shared.

### scheduled_workouts and rotation state

The old model pinned each session to a `scheduled_for` date with a `mesocycle_week`.
Pure rotation needs a position, not a calendar grid.

- Add a per-user-per-program rotation state. Either a new `program_progress` table
  (`user_id`, `program_id` unique together, `current_slot_index`,
  `current_microcycle_number`, `current_repetition`, `in_deload` bool,
  `last_completed_at`) or equivalent columns on the active program. A table is
  cleaner because progress is per user and the same program can be shared.
- `scheduled_workouts` stays for the calendar surface but `scheduled_for` becomes
  nullable. A session can be "the next slot in the rotation" with no fixed date.
  Keep `is_deload`; replace `mesocycle_week` with `microcycle_number` and
  `repetition`.
- "Today's session" is computed as the slot at `current_slot_index`. Completing it
  advances the position: increment the slot index, wrap to 0 at microcycle end and
  bump the repetition, and after the Nth repetition enter the deload (if enabled)
  then start the next mesocycle.
- **Skipping** a session advances the position the same way completing it does (the
  slot is consumed, not repeated) but marks the session `skipped`. See
  `05-active-session.md` for the in-session skip and its progression neutrality.

### session-level divergence (cross-reference)

In-session exercise swaps, permanent edits, and skips are specified in
`05-active-session.md`. Two recording needs land outside the program tables:

- `workout_exercises.substituted_for_exercise_id` nullable: set when an exercise is
  temporarily swapped for a session, linking the substitute back to the original so
  the progression engine pauses (does not stall) the original.
- `scheduled_workouts.status = skipped`: consumed by the rotation advance above and
  ignored by the progression engine when counting successes or failures.

These live on the tracking tables (`02-tracking` in the archive) but the rotation and
progression hooks they depend on are defined here.

### enums

No enum changes required. `periodization_mode`, `intensity_mode`, `rep_mode`,
`progression_strategy` all carry over from migration 0026.

## 3. Migration

One Alembic migration, next in sequence after `0026`. Name it for the change, for
example `0027_flexible_microcycle_mesocycle`.

Steps:

1. Add new columns (`programs.microcycle_length`, `program_days.slot_index`,
   `program_days.is_rest_day`, `program_progress` table) as nullable or with
   defaults so the migration can backfill.
2. Backfill: for existing programs, set `microcycle_length = days_per_week`, copy
   `day_index` into `slot_index`, set `is_rest_day = false` everywhere, and set
   `mesocycle_length_microcycles = mesocycle_length_weeks`.
3. Make the new columns non-nullable once backfilled.
4. Drop `days_per_week` and `weeks` from `programs` and `program_templates`, drop
   `day_index` from `program_days`, drop `mesocycle_length_weeks`.
5. Migrate `scheduled_workouts`: add `microcycle_number`, `repetition`, make
   `scheduled_for` nullable, backfill from `mesocycle_week`, drop `mesocycle_week`.

This is a breaking change to the API contract, which is acceptable: the maintainer
approved full-stack changes and the user base is the maintainer plus a few partners.
Reseed program_templates from the updated seed script rather than backfilling jsonb
by hand.

## 4. API changes

Under `/v1/programs`. Keep the response envelope in `00-overview/api-conventions.md`.

- `POST /v1/programs` creates a blank program with no slots, `microcycle_length` 0,
  and sensible defaults (goal general, intensity_mode off, mesocycle_length 4). It
  must not hard-code 6 weeks or 4 days. See the bug in `archive/programs-workflow-original-feedback.md`.
- `PATCH /v1/programs/{id}` edits name, goal, periodization_mode,
  `mesocycle_length_microcycles`, `auto_deload`, `intensity_mode`.
- Slot endpoints: add, remove, reorder, and toggle `is_rest_day` on slots.
  `microcycle_length` is recomputed server-side from the slot count on every change;
  the client never sets it directly.
- `POST /v1/programs/{id}/activate` and `POST /v1/programs/{id}/deactivate`.
  Activation requires at least one training slot, not a match against `days_per_week`.
  Deactivating clears `is_active` and leaves `program_progress` intact so
  re-activation resumes where it left off.
- `GET /v1/programs/{id}/position` returns the current rotation position and the
  computed "today" slot. Replaces the week-based mesocycle endpoint.
- Template copy (`POST /v1/programs/from-template/{slug}`) clones the template
  `data.slots` into a new fully editable program with `source = copied` and
  `template_id` set for provenance only; edits never write back to the template.
- **Duplicate** (`POST /v1/programs/{id}/duplicate`) clones an existing program owned
  by the user into a new editable program (`source = copied`, `template_id` null, name
  suffixed "(copy)"), inactive, with fresh rotation state. A straight fork, not a
  template.
- **Save as template** (`POST /v1/programs/{id}/save-as-template`) creates a
  `program_templates` row from the program with `owner_id` = the user and a chosen
  `visibility` (`private` or `shared`) and name. The program itself is unchanged. The
  saved template is then usable through the same `from-template` copy path as curated
  ones.
- The template list endpoint (`GET /v1/programs/templates`) returns curated templates,
  the requester's own private templates, and all `shared` templates. The Browse
  templates UI groups them (see `02-programs-screens.md`).

Regenerate `packages/openapi/openapi.json` and the web types
(`pnpm openapi:generate`) after the backend lands.

## 5. Validation rules

- A program activates if it has at least one training slot. Rest-only programs cannot
  activate.
- `mesocycle_length_microcycles >= 1`.
- `microcycle_length` always equals the slot count; reject client writes that disagree.
- Deload is only meaningful when `auto_deload` is true; the deload microcycle is not a
  user-built slot list in v1, it is generated by the progression engine (out of scope
  here, see `archive/phases-original/04-progression`).

## 6. Acceptance

- [ ] A new program is created empty, with no forced 6-week or 4-day defaults.
- [ ] A user can add any number of slots; `microcycle_length` tracks the count.
- [ ] Slots can be marked rest days and reordered.
- [ ] Activation succeeds with any number of training slots and fails only when there
      are zero. The old "Program has 0 days but 4 are required" error is gone.
- [ ] Choosing periodization sets `mesocycle_length_microcycles` (deload excluded).
- [ ] An active program can be deactivated and re-activated, resuming its position.
- [ ] Template use produces an independent, fully editable copy.
- [ ] A program can be duplicated into a new editable program (fork, no template link).
- [ ] A program can be saved as a template with a chosen visibility (private or shared);
      private templates show only to the owner, shared ones to all partners.
- [ ] `data-model.md` updated; OpenAPI and web types regenerated; backend tests pass.

## 7. Out of scope

- Progression-engine math for the deload microcycle (separate feature).
- iOS data layer (still unwired; catches up after web).
- Calendar date pinning (the hybrid option was not chosen; rotation only).
