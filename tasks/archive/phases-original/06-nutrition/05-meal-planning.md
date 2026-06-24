# 06.05 Meal planning

## Context

`06.03 Meal logging and meal plans` shipped a basic single meal plan with target macros and a `days` jsonb blob. Users want real meal planning with several shapes and several levels of strictness. This task replaces that basic plan model with a structured one.

What users want to build:

1. A single day plan that repeats every day.
2. Separate training day and rest day plans, then either set them across the week or month by hand, or sync them to the active training program so workout days use the training plan and off days use the rest plan.
3. A weekly plan (seven day templates) that resets at the end of the week so the user can update macros or calories for the next week.

How strict a plan is, chosen per plan:

- Targets only, no meals. The user just sets numbers and tracks against them.
- Meals only. The user enters meals and we total the macros and calories from the foods. Meal times are optional (with or without timestamps).
- Targets and meals together.

And the user can choose what to track against, independent of meals:

- Ignore the meal plan and plan using calories only.
- Macros only.
- Macros and calories.

Reference: `06-nutrition/03-meal-logging.md`, `06-nutrition/04-nutrition-api-integration.md`, `03-programming/03-scheduling.md`, `00-overview/data-model.md` (meal_plans).

## Goal

A meal plan builder and API that supports daily repeating, training and rest day, and weekly resetting plans, with per-plan choices for whether the plan carries meals, targets, or both, and what is tracked (calories, macros, or both).

## Data model

Replace the single `meal_plans.days` jsonb blob with structured tables. Migrate any existing plans into the new shape.

- `meal_plans`: `id`, `user_id`, `name`, `is_active` (one active per user),
  - `plan_kind` enum: `daily_repeating`, `training_rest`, `weekly`.
  - `content_mode` enum: `targets_only`, `meals_only`, `targets_and_meals`.
  - `tracking_mode` enum: `calories_only`, `macros_only`, `macros_and_calories`.
  - default targets `target_kcal`, `target_protein_g`, `target_carbs_g`, `target_fat_g` (used when a day has no per-day targets, or when `content_mode = targets_only`).
  - `week_resets` bool and `week_start_dow` smallint for weekly plans.
  - `synced_to_program` bool for training_rest plans that follow the active program.
- `meal_plan_days`: a plan has one or more day templates.
  - `id`, `meal_plan_id`, `day_role` enum: `every_day`, `training`, `rest`, or `dow_0` through `dow_6` for weekly.
  - optional per-day `target_kcal`, `target_protein_g`, `target_carbs_g`, `target_fat_g` (override the plan defaults).
- `meal_plan_meals`: planned meals inside a day template.
  - `id`, `meal_plan_day_id`, `name` (Breakfast, Pre workout, etc.), `slot_index`, optional `planned_time` (nullable so timestamps stay optional).
- `meal_plan_items`: planned foods inside a planned meal.
  - `id`, `meal_plan_meal_id`, `food_id`, `amount`, `unit` (g, ml, or a `food_servings` serving), `grams` resolved, plus denormalized `kcal`, `protein_g`, `carbs_g`, `fat_g` at the chosen amount.
- Totals: a day template total is the sum of its meals, each meal the sum of its items. When `content_mode` includes meals, day targets default to those totals unless the user overrode them.

## Assignment to the calendar

- `daily_repeating`: the single `every_day` template applies to every date.
- `training_rest`: the user maps training and rest templates to dates one of two ways:
  - manual: pick which weekdays (or specific dates across the month) are training vs rest.
  - synced: when `synced_to_program` is on, a date uses the training template if the active program schedules a workout that day, otherwise the rest template. Reuse the scheduling data from `03.03`.
- `weekly`: each date uses the `dow_n` template for its weekday. If `week_resets` is on, at the configured week start we prompt the user to review and update next week's targets or meals before the new week becomes active.

## API

- `POST /v1/meal-plans` create with `plan_kind`, `content_mode`, `tracking_mode`, defaults, and nested day templates, meals, and items.
- `GET /v1/meal-plans` list, `GET /v1/meal-plans/{id}` full structure.
- `PATCH /v1/meal-plans/{id}` and nested edit or delete for days, meals, items.
- `POST /v1/meal-plans/{id}/activate` (one active per user).
- `GET /v1/meal-plans/active` returns the active plan and, for a given date, the resolved day template (training vs rest vs weekday) with its targets and planned meals.
- `GET /v1/meal-plans/{id}/day?date=...` resolves which template applies on that date and returns it.
- Weekly reset: a small job or on-read check that, at `week_start_dow`, flags the plan as needing review and exposes that state so the client can prompt for target updates.

## Web UI

Route group under `/nutrition/plans`.

- Plan create wizard:
  1. Pick plan kind: every day, training and rest, or weekly.
  2. Pick content mode: targets only, meals only, or both.
  3. Pick tracking mode: calories only, macros only, or macros and calories. The rings and bars on the nutrition page follow this choice.
  4. For training and rest: choose manual weekday mapping or sync to the active program.
  5. For weekly: toggle end of week reset and the week start day.
- Day template editor: add meals, optionally set a time per meal, add foods to each meal via the shared ingredient picker (search through FatSecret, barcode scan, or manual), with the amount in g, ml, or a named serving. Show running per meal and per day totals. The same picker is specified in `06.06`.
- A plan summary showing each day template with its totals and which dates it covers.

## Deliverables

1. Migrations for the new meal plan tables and enums, with a data migration off the old `days` blob.
2. Full meal plan API including activation, calendar resolution, program sync, and weekly reset state.
3. Web plan wizard and day template editor reusing the ingredient picker from `06.06`.
4. Totals math (item to meal to day) and target derivation rules per content mode.
5. Tests: training vs rest resolution by program schedule; weekly template resolves by weekday; weekly reset flips review state at week start; totals roll up correctly; tracking_mode drives which targets are returned.

## Acceptance criteria

- A user can create a daily repeating plan and see the same targets and planned meals every day.
- A user can create training and rest plans, sync them to the program, and have workout days show the training plan automatically.
- A weekly plan shows a different template per weekday and asks the user to update targets when the week resets.
- A user can build a meals only plan and the day targets come from the summed foods, with meal times optional.
- Choosing calories only, macros only, or macros and calories changes what the nutrition page tracks against.

## Dependencies

- `06.03 Meal logging and meal plans` (replaces its plan model)
- `06.04 Nutrition database API (FatSecret)` (ingredient search and servings)
- `06.06 Meal plan logging and flexible tracking` (shared ingredient picker)
- `03.03 Scheduling` (program sync for training vs rest)

## Out of scope

- Logging and meal completion against a plan (task `06.06`).
- iOS parity (follow-up under `08-ios/`).
- Auto generated plans from a target (later).
