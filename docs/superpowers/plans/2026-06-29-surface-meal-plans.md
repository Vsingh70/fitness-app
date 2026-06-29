# Surface Meal Plans (Programs-parity) Implementation Plan

> **For agentic workers:** Run each numbered task through `/loop` (builder + checker) one at a time, in order, reviewing between tasks. A task is done only when its Definition of Done (all listed checks) is green. Follow the CLAUDE.md loop stop rules. Never weaken a test/type/lint to go green.

**Goal:** Make the existing multi-plan + edit-after-activate meal-plan flow discoverable on web, at parity with Programs (Nutrition-hub entry + Settings "Active meal plan" section), and add the one missing backend piece (deactivate).

**Architecture:** Surfacing + parity only — no new data model. The `meal_plans` model/router/service, the `/nutrition/plans` library + editor + create wizard, activation, and the one-active partial-unique index all already exist. We add a `deactivate` endpoint (mirroring Programs), its web client/hooks, a Settings "Active meal plan" section, and a Nutrition-day header entry. Spec: `docs/superpowers/specs/2026-06-29-surface-meal-plans-design.md`.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (apps/api); Next.js + React + TanStack Query + Tailwind (apps/web); pytest/ruff/mypy; vitest/tsc/eslint/prettier.

**Patterns to mirror (read these first):**
- Backend deactivate: `apps/api/app/services/programs.py` `deactivate_program` (~L675-681) + `apps/api/app/routers/programs.py` `POST /v1/programs/{id}/deactivate` (~L332-341).
- Existing meal-plan activate (the template to copy): `apps/api/app/services/meal_plans.py` `activate_plan` (~L460-475) + `apps/api/app/routers/meal_plans.py` `POST /meal-plans/{id}/activate` (~L137-145).
- Web deactivate: `apps/web/src/lib/api/programs.ts` `deactivateProgram` + `apps/web/src/lib/hooks/programs.ts` `useDeactivateProgram` / `useDeactivateAnyProgram`.
- Settings section: the "Active program" block in `apps/web/src/app/(app)/settings/page.tsx` (NAV "Training" group + its Section).
- Existing meal-plan web client/hooks to extend: `apps/web/src/lib/api/meal-plans.ts`, `apps/web/src/lib/hooks/meal-plans.ts`.

---

## Task 1: Backend — deactivate a meal plan

**Files:**
- Modify: `apps/api/app/services/meal_plans.py` (add `deactivate_plan`)
- Modify: `apps/api/app/routers/meal_plans.py` (add `POST /meal-plans/{plan_id}/deactivate`)
- Test: `apps/api/tests/test_meal_plans_structured.py` (add deactivate test)
- Regen: `packages/openapi/openapi.json`

**What to build** (mirror `programs.deactivate_program`):
- `async def deactivate_plan(session, user, plan_id) -> MealPlan`: load the user-owned plan (reuse the existing `_owned_plan` helper), set `is_active = False` and `updated_at = _now()`, `flush`, return the refreshed plan (reuse `_refresh`). No-op-safe when already inactive (don't error). Does NOT touch the plan's days/meals/items or any logged meals.
- Router: `@router.post("/meal-plans/{plan_id}/deactivate", response_model=MealPlanResponse)` calling the service then `await session.commit()`, mirroring the existing `/activate` handler exactly.

**Test (add to test_meal_plans_structured.py):** create a plan → activate it (assert `is_active` true) → `POST /v1/meal-plans/{id}/deactivate` → 200 and `is_active` false; then deactivate again → still 200, still false (idempotent); and confirm a separate activate still enforces single-active (existing invariant unbroken).

**Then regenerate the contract:** `cd apps/api && uv run python -m scripts.export_openapi > ../../packages/openapi/openapi.json` and include it in the commit.

**Definition of Done (checker runs, all must pass):**
- `cd apps/api && uv run pytest -q` (new test + full suite green; run with `TZ=UTC` to avoid the known local body-metrics tz flake)
- `cd apps/api && uv run ruff check . && uv run ruff format --check .`
- `cd apps/api && uv run mypy app`
- OpenAPI committed and drift-free (re-running the export produces no diff)

---

## Task 2: Web — deactivate client + hooks + regen types

**Files:**
- Modify: `apps/web/src/lib/api/meal-plans.ts` (add `deactivateMealPlan`)
- Modify: `apps/web/src/lib/hooks/meal-plans.ts` (add `useDeactivateMealPlan`, `useDeactivateAnyMealPlan`)
- Regen: `apps/web/src/lib/api/types.ts` (from Task 1's OpenAPI)

**What to build** (mirror the program equivalents):
- `deactivateMealPlan(id: string): Promise<MealPlan>` → `api.post("/v1/meal-plans/${id}/deactivate")`.
- `useDeactivateMealPlan()` and `useDeactivateAnyMealPlan()` (the latter takes the id at call time, like `useDeactivateAnyProgram`, for use from Settings). On success invalidate the SAME query keys the existing meal-plan mutations invalidate (`["meal-plans"]`, `["meal-plan","active"]`, `["nutrition"]`, `["nutrition.targets"]`) — copy that invalidation set from the existing `useActivateMealPlan`.

**First:** `cd apps/web && pnpm openapi:generate` so `types.ts` includes the new `/v1/meal-plans/{id}/deactivate` path.

**Definition of Done:**
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm lint`
- `cd apps/web && pnpm format:check`
- `cd apps/web && pnpm test` (no regressions)

---

## Task 3: Web — Settings "Active meal plan" section

**Files:**
- Modify: `apps/web/src/app/(app)/settings/page.tsx`
- Test: `apps/web/tests/settings-active-meal-plan.test.tsx`

**What to build** (mirror the "Active program" Training section):
- Add a `{ id: "meal-plan", label: "Active meal plan" }` item to the existing `NAV` "Nutrition" group.
- Add a `Section id="meal-plan"` that uses `useMealPlans()` to find the active plan (`items.find(p => p.is_active)`):
  - If active: show its name + "activated {relativeTime(activated_at)}"; a **Deactivate** button wired to `useDeactivateAnyMealPlan()` (`.mutate(plan.id)`, toast on success/error, like the program deactivate); and a **Switch / Browse meal plans** link to `/nutrition/plans`.
  - If none active: a short empty state + a **Browse meal plans** link to `/nutrition/plans`.
- Match the existing section's styling/components (Card, Button, SettingRow, RevealItem) — read the "Active program" block and copy its shape.

**Test:** render the settings page (or the extracted section) with `useMealPlans` mocked (mock `@/lib/hooks/meal-plans`): (a) with an active plan → asserts the plan name renders and clicking Deactivate calls the deactivate mutation with the plan id; (b) with no active plan → asserts the "Browse meal plans" link to `/nutrition/plans` renders. Follow the existing web test conventions (vi.mock for hooks; `tests/program-library.test.tsx` is a good template).

**Definition of Done:**
- `cd apps/web && pnpm test` (new test passes + no regressions)
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm lint`
- `cd apps/web && pnpm format:check`

---

## Task 4: Web — Nutrition-day hub entry point

**Files:**
- Modify: `apps/web/src/components/nutrition/nutrition-day.tsx`
- Test: `apps/web/tests/nutrition-meal-plans-entry.test.tsx`

**What to build:** In the nutrition day header (next to the `NutritionModeControl`), add:
- A persistent **"Meal plans"** link/button → `/nutrition/plans` (the existing library), styled as a small header action.
- When a plan is active (derive from `useMealPlans()` `items.find(p => p.is_active)`, or from the already-present `useActivePlan` data's `plan.id`), an **active-plan chip** showing the plan name that links to `/nutrition/plans/${activePlanId}` (the editor) — so editing the active plan is one tap from the day view.

**Test:** render `NutritionDay` (mock the meal-plan + me hooks as the other nutrition tests do): asserts a link to `/nutrition/plans` is present; and, when an active plan is mocked, a chip/link to `/nutrition/plans/{id}` with the plan name is present. Use jsdom + the existing nutrition test setup (the Pointer-Capture/scrollIntoView polyfills in `tests/setup.ts` already exist for `<Sheet>`).

**Definition of Done:**
- `cd apps/web && pnpm test` (new test passes + no regressions)
- `cd apps/web && pnpm typecheck`
- `cd apps/web && pnpm lint`
- `cd apps/web && pnpm format:check`

---

## After all tasks (integration + ship)
- Full green: `apps/api` (pytest TZ=UTC / ruff / mypy / no OpenAPI drift) and `apps/web` (test / typecheck / lint / format:check).
- Manual e2e: Nutrition → "Meal plans" → create + activate + edit a plan; the active-plan chip opens the editor; Settings "Active meal plan" → switch / deactivate; daily logging still works in both flexible and plan modes.
- Ship via the ship-flow (this branch `feat/surface-meal-plans` → PR → squash-merge); confirm web (Vercel) deploy. (No API behavior change beyond the additive deactivate endpoint; the api-deploy CD will pick it up.)

## Self-review (done)
- **Spec coverage:** entry point (Task 4), Settings section (Task 3), deactivate backend (Task 1) + web (Task 2) — all spec items covered.
- **No new placeholders:** each task names exact files, the pattern to mirror, the test to write, and concrete DoD checks.
- **Type/name consistency:** `deactivateMealPlan` / `useDeactivateMealPlan` / `useDeactivateAnyMealPlan` used consistently across Tasks 2–3; endpoint path `/v1/meal-plans/{id}/deactivate` consistent across Tasks 1–2.
