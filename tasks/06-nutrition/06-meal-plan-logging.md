# 06.06 Meal plan logging and flexible tracking

## Context

With structured meal plans in place (`06.05`), logging should be fast when a plan is active and still flexible when it is not. Two paths:

1. Plan active: the user should be able to mark a planned meal complete in one tap instead of logging every food. They can still edit serving sizes, swap the whole meal, or delete it, and deleting should let them choose just today or forever.
2. Flexible tracking: the user wants to track a meal that is not in the plan. They build it from ingredients entered manually, searched from the nutrition database, or scanned by barcode, choose how much of each they used in g, cups, or servings, and add as many ingredients as the meal has.

The ingredient picker built here is the same one meal plan creation uses in `06.05`.

Reference: `06-nutrition/03-meal-logging.md`, `06-nutrition/04-nutrition-api-integration.md`, `06-nutrition/05-meal-planning.md`, `00-overview/data-model.md` (meals, meal_items).

## Goal

A nutrition logging experience that turns a planned day into one tap per meal, with easy edit, swap, and delete, plus a flexible multi ingredient meal builder for anything off plan. Logging materializes real `meals` and `meal_items` rows so history and daily totals stay accurate.

## Mark meal complete (plan active)

- For each planned meal on today's resolved day template, show a "Mark complete" action.
- Completing materializes a real `meal` row plus `meal_items` copied from the planned items (food, amount, resolved grams, denormalized macros), with `eaten_at` set to the planned time if present else now.
- A completed meal links back to its source planned meal so the UI can show plan adherence.
- Edit a completed meal:
  - change serving sizes per item (re denormalize macros),
  - swap the whole meal for a different planned meal or a freshly tracked one,
  - delete it.
- Delete scope: when deleting a planned or completed meal, ask "just today" or "forever".
  - just today: remove only today's logged meal (and skip the plan slot for today).
  - forever: also remove the meal from the plan day template so it stops appearing on future days.

## Flexible meal tracking (any time)

- A "Track a meal" action opens the meal builder.
- Add ingredients three ways, all feeding the same row:
  - manual entry: name plus macros per amount, optionally saved as a custom food (`06.01` custom CRUD).
  - search: the FatSecret backed search from `06.04`.
  - barcode: the barcode lookup from `06.04`.
- For each ingredient choose the amount and unit: grams, milliliters, or a named serving from `food_servings` (for example 1 cup, 1 serving). Convert to grams for the macro math.
- Add as many ingredients as needed. Show running meal totals as items are added or amounts change.
- Save creates a `meal` plus its `meal_items`. Optional `eaten_at` timestamp.

## Shared ingredient picker

- One component used by both meal plan creation (`06.05`) and flexible tracking here.
- Tabs: Search, Scan, Manual. Returns a chosen food plus amount and unit, with the resolved grams and macros at that amount.
- It must handle a food that exposes several servings and let the user pick which serving the amount is in.

## API

- `POST /v1/meal-plans/{plan_id}/meals/{planned_meal_id}/complete?date=...` materializes the planned meal into a logged meal for that date and returns it.
- `PATCH /v1/meals/{id}` and `PATCH /v1/meal-items/{id}` cover serving edits and swaps (reuse `06.03`).
- `DELETE /v1/meals/{id}?scope=today|forever`:
  - `today` soft deletes the logged meal only.
  - `forever` soft deletes the logged meal and removes the matching `meal_plan_meal` from the template.
- Flexible tracking reuses `POST /v1/meals` plus `POST /v1/meals/{id}/items` from `06.03`, with item bodies accepting `amount` and `unit` (g, ml, or serving id) and the server resolving grams and denormalizing macros.

## Web UI

Route: `/nutrition` (today).

- When a plan is active: render today's resolved day template as a checklist of meals, each with a one tap Mark complete, and a row menu for edit, swap, and delete with the today or forever choice.
- When no plan is active, or for any extra meal: a prominent "Track a meal" button opens the meal builder with the shared ingredient picker.
- Daily totals (rings and bars) follow the plan's `tracking_mode` from `06.05` (calories only, macros only, or both), and update instantly on complete, edit, or track.

## Deliverables

1. Meal complete endpoint that materializes planned meals into logged meals and items.
2. Delete with today vs forever semantics across the logged meal and the plan template.
3. Edit and swap on completed meals with macro re denormalization.
4. The shared ingredient picker component (Search, Scan, Manual) used here and in `06.05`.
5. Item bodies accepting g, ml, or a named serving, with server side gram resolution.
6. Tests: complete materializes correct items and totals; delete forever removes the template meal while delete today does not; serving edit re denormalizes; a multi ingredient tracked meal totals correctly; serving to gram conversion is correct.

## Acceptance criteria

- With a plan active, a user can log a full planned day by tapping Mark complete on each meal, in well under a minute.
- Editing a completed meal's serving size updates that meal and the daily totals immediately.
- Deleting a meal forever stops it appearing on future plan days; deleting just today leaves the plan intact.
- A user can build an off plan meal from three or more ingredients across manual, search, and barcode, each in its own unit, and save it with correct totals.

## Dependencies

- `06.03 Meal logging and meal plans` (base meals and items API)
- `06.04 Nutrition database API (FatSecret)` (search, barcode, servings)
- `06.05 Meal planning` (plan structure, resolved day templates, tracking mode)

## Out of scope

- Recipe builder and saved meals library (later).
- iOS parity (follow-up under `08-ios/`).
- Photo recognition.
