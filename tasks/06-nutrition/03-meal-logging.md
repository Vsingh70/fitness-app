# 06.03 Meal logging and meal plans

## Context

Now we tie food entry into actual logged meals and structured meal plans.

Reference: `00-overview/data-model.md` (meals, meal_items, meal_plans).

## Goal

Full meal logging on web (entry, edit, delete, daily totals) and a meal plan builder.

## Meals API

- `POST /v1/meals` create with `eaten_at`, `meal_type`, optional `photo_url` (from a separate upload step or from a recognize call).
- `GET /v1/meals` list, filters: `from`, `to`, `meal_type`.
- `GET /v1/meals/{id}`.
- `PATCH /v1/meals/{id}`.
- `DELETE /v1/meals/{id}` soft delete.
- `POST /v1/meals/{id}/items` body `{ food_id, grams }`. Server denormalizes macros into the item row.
- `PATCH /v1/meal-items/{id}`.
- `DELETE /v1/meal-items/{id}`.

## Daily summary

- `GET /v1/nutrition/day?date=2026-05-25` returns totals (kcal, protein, carbs, fat, fiber) and a per-meal breakdown.

## Meal plans

- `POST /v1/meal-plans` body includes targets and an optional `days` jsonb structure of suggested foods per slot.
- `POST /v1/meal-plans/{id}/activate` makes it the active plan; only one active per user.
- `GET /v1/meal-plans/active` returns active plan + today's progress vs targets.

## Macro targets

If no meal plan is active, derive defaults from user profile:
- Maintenance kcal: Mifflin-St Jeor based on age, sex_at_birth, height, weight, activity factor.
- Protein default: 2.0 g/kg bodyweight.
- Fat default: 25% of kcal.
- Carbs default: remainder.

User can override on the settings page.

## Web UI

Route: `/nutrition` (today by default).

Layout:
- Top: ring chart for kcal vs target, three small bars for protein/carbs/fat.
- Meal sections: Breakfast, Lunch, Dinner, Snacks. Each shows items, allows adding via search, barcode, or photo.
- Sticky bottom FAB on mobile: "+ Add food" opens a sheet with three tabs (Search, Scan, Photo).
- `/nutrition/history` shows weekly averages and adherence calendar.
- `/nutrition/plans` lets the user create/edit/activate plans.

## Deliverables

1. All endpoints.
2. Denormalization logic for `meal_items`.
3. Web UI.
4. Profile fields needed for Mifflin-St Jeor: add `height_cm`, `weight_kg` (latest known) to `users` schema if not already there; allow daily weight logging via `POST /v1/body-metrics` (separate small table `body_metrics(user_id, recorded_at, weight_kg, body_fat_pct)`).
5. Tests for daily totals math, plan activation, target derivation.

## Acceptance criteria

- Adding a food via search updates daily totals instantly.
- Switching active meal plan updates target rings.
- A user can log a full day of meals via the web in under 3 minutes when they reuse common foods.

## Dependencies

- `06.01 Food database, barcode, and search`
- `06.02 AI meal photo recognition`

## Out of scope

- Recipe builder (later).
- Restaurant menu integration (later).
