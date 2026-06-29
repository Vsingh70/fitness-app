# Surface meal plans (Programs-parity) — design

**Date:** 2026-06-29
**Status:** approved (brainstorming) → ready for implementation plan
**Scope:** web only

## Context

The user asked to "edit a meal plan after starting one" and "create multiple meal
plans, like the program → workouts workflow." Investigation found **these already
exist** in the web app:

- **Multiple plans:** library at `/nutrition/plans` + create wizard
  (`components/nutrition/plan-create-wizard.tsx`); unlimited plans per user.
- **Active plan (like Programs):** `meal_plans.is_active` + `activated_at`, a
  partial unique index (one active per user), and `POST /v1/meal-plans/{id}/activate`.
- **Edit after starting:** the editor at `/nutrition/plans/[id]` edits
  days/meals/items with **no lock**, active or not.

The real gap (confirmed with the user) is **discoverability**: Programs is a
top-level nav tab (`/programs`), but meal-plan management is reachable only via the
"Plan" mode toggle on the nutrition day header — there's no obvious entry, no
Settings surface, and (unlike Programs) no Deactivate.

Decision: **fold meal plans into the Nutrition hub** (no new nav tab — the mobile
tab bar is intentionally capped at 5; matches the app's "Exercises folds into the
Workouts hub" pattern). This is surfacing + Programs-parity, **not** a new
data model.

## Design

### 1. Nutrition hub entry point (the core fix)
In the nutrition day header (`apps/web/src/components/nutrition/nutrition-day.tsx`,
beside the Flexible/Plan `NutritionModeControl`):
- A **"Meal plans"** action → links to `/nutrition/plans` (existing library).
- When a plan is active, an **active-plan chip** (plan name) → links to that plan's
  editor `/nutrition/plans/[id]`, so editing the active plan is one tap from the
  day you're already on. Uses `useActivePlan` / `useMealPlans` (already imported in
  nutrition-day).

### 2. Settings "Active meal plan" section
In `apps/web/src/app/(app)/settings/page.tsx`, add a section mirroring the existing
"Active program" block (it already uses `useMyPrograms` + `useDeactivateAnyProgram`):
- Show the active plan (name + "activated X ago"); actions: **Switch** (browse →
  `/nutrition/plans`), **Deactivate**, **Browse meal plans**.
- New nav group entry under "Nutrition" (the NAV array already has a Nutrition group).
- Uses `useMealPlans` + the new `useDeactivateAnyMealPlan`.

### 3. Deactivate parity (the only genuinely-missing backend bit)
Programs has activate **and** deactivate; meal plans only has activate. Mirror
`programs.deactivate_program` / `POST /v1/programs/{id}/deactivate`:
- **API:** `deactivate_plan(session, user, plan_id)` in
  `apps/api/app/services/meal_plans.py` (set `is_active=False`, keep the plan;
  no-op-safe) + `POST /v1/meal-plans/{plan_id}/deactivate` in
  `apps/api/app/routers/meal_plans.py`. Regenerate OpenAPI
  (`scripts/export_openapi.py`) + `pnpm openapi:generate`.
- **Web:** `deactivateMealPlan(id)` in `apps/web/src/lib/api/meal-plans.ts` +
  `useDeactivateMealPlan()` / `useDeactivateAnyMealPlan()` in
  `apps/web/src/lib/hooks/meal-plans.ts` (mirror the program hooks; invalidate the
  meal-plan + active + nutrition query keys).

## Out of scope (YAGNI)
- New data model / schema migration.
- Multiple *simultaneously*-active plans (one-active is correct, same as Programs).
- iOS (its meal-plans screen is mock-only; tracked separately).
- Daily-logging behavior and the `/nutrition/plans` library + editor + wizard
  (already work; left as-is aside from the header entry).

## Reused building blocks
- API: `meal_plans` model/router/service (activate, nested CRUD), the active
  partial-unique index — all exist; only `deactivate` is added.
- Web: `useMealPlans`, `useActivePlan`, `useActivateMealPlan`,
  `meal-plans.ts` client, the plans library + editor + wizard; the Programs
  "Active program" Settings block as the template for the new section.

## Verification
- **API:** `uv run pytest -q` (Docker), `ruff`, `mypy app`; a new test: activate a
  plan then deactivate → `is_active` false and the one-active invariant still holds;
  no OpenAPI drift after regen (the new endpoint is committed).
- **Web:** `pnpm test`, `typecheck`, `lint`, `format:check`; tests for the Settings
  "Active meal plan" section (renders active plan; deactivate action) and the
  nutrition-header entry (renders "Meal plans" link; active-plan chip when active).
- **Manual e2e:** Nutrition → "Meal plans" → create/activate/edit a plan; the
  active-plan chip opens the editor; Settings shows the active plan with
  switch/deactivate.
