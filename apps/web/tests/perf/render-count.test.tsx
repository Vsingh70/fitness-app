import { memo, useState, type ComponentType } from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FoodRow } from "@/components/nutrition/ingredient-picker";
import { MealRow, type MealRowModel } from "@/components/nutrition/meal-list";
import { SetRow } from "@/components/workouts/set-row";
import type { FoodResponse } from "@/lib/api/nutrition";

import { RENDER } from "./budgets";

/**
 * Re-render budget for the hot leaf components.
 *
 * These leaves are rendered many times per screen — SetRow per set in an active
 * workout, MealRow per meal in the nutrition day, FoodRow per search result. The
 * audit found zero React.memo in the codebase, so leaves re-rendered whenever an
 * unrelated ancestor updated. Each test pins that cost: it gives the leaf stable
 * props, forces unrelated parent state changes, and counts how many extra times
 * the leaf's render function actually runs.
 *
 * Why not React.Profiler: a Profiler's `onRender` fires for the Profiler's own
 * parent-driven re-render even when its memoized child bails out, so it counts the
 * wrapper rather than the leaf (always == the number of parent updates, regardless
 * of memoization). Instead we drive each leaf's real render function — `memo().type`
 * — through a memo boundary that mirrors the leaf's own `React.memo`, and count how
 * often that render function runs. A leaf that regresses to a plain (un-memoized)
 * function has no `.type`, so `memoInner` throws and the test fails — catching the
 * regression. A properly memoized leaf with stable props records 0 extra renders.
 *
 * It is a ratchet: the budgets in perf/budgets.json are pinned at 0 (fully
 * memoized). Any regression that breaks memoization fails the suite.
 */

const BUMPS = 4;

// Stable module-scope props so a memoized leaf bails out on parent re-render.
const NOOP = () => {};

const MEAL_ROW_MODEL: MealRowModel = {
  key: "meal-1",
  name: "Breakfast",
  mealId: null,
  sourcePlanMealId: null,
  eatenAt: null,
  items: [],
  onAddFood: NOOP,
};
const EMPTY_FOOD_LOOKUP = new Map<string, FoodResponse>();

const FOOD: FoodResponse = {
  id: "food-1",
  name: "Oats",
  brand: null,
  archived_at: null,
  carbs_g_per_100g: "60",
  created_at: "2026-06-24T00:00:00Z",
  external_id: null,
  fat_g_per_100g: "7",
  fiber_g_per_100g: null,
  kcal_per_100g: "380",
  owner_id: null,
  payload: {},
  protein_g_per_100g: "13",
  serving_label: null,
  serving_size_g: "100",
  servings: [],
  source: "user",
};

/** The real render function inside a `React.memo` leaf; throws if not memoized. */
function memoInner<P>(Leaf: ComponentType<P>): ComponentType<P> {
  const inner = (Leaf as unknown as { type?: ComponentType<P> }).type;
  if (typeof inner !== "function") {
    throw new Error("expected a React.memo component (no .type render function found)");
  }
  return inner;
}

/**
 * Renders `Leaf` with stable `props` under a parent that bumps unrelated state
 * `BUMPS` times, and returns how many EXTRA times the leaf's render function ran
 * (0 means it bailed out on every unrelated update — the memoized ideal).
 */
async function countExtraRenders<P extends object>(
  Leaf: ComponentType<P>,
  props: P,
): Promise<number> {
  const Inner = memoInner(Leaf);
  let renders = 0;
  // Mirror the leaf's own React.memo so the bail-out we measure is the leaf's.
  const Probe = memo(function Probe(p: P) {
    renders += 1;
    return <Inner {...p} />;
  });

  function Harness() {
    const [n, setN] = useState(0);
    return (
      <div>
        <button type="button" onClick={() => setN((x) => x + 1)}>
          bump {n}
        </button>
        <Probe {...props} />
      </div>
    );
  }

  const user = userEvent.setup();
  render(<Harness />);
  const bump = screen.getByRole("button", { name: /bump/i });
  for (let i = 0; i < BUMPS; i += 1) {
    await user.click(bump);
  }
  return renders - 1; // discount the initial mount render
}

describe("render-count budget (ratchet)", () => {
  it(`SetRow renders at most ${RENDER.setRowUnrelatedRerendersMax}x extra on ${BUMPS} unrelated parent updates`, async () => {
    const extra = await countExtraRenders(SetRow, {
      trackingType: "weight_reps" as const,
      setIndex: 0,
      onSubmit: NOOP,
    });
    expect(
      extra,
      `SetRow's render ran ${extra} extra time(s) on ${BUMPS} unrelated parent updates. ` +
        `A memoized leaf with stable props should stay at 0.`,
    ).toBeLessThanOrEqual(RENDER.setRowUnrelatedRerendersMax);
  });

  it(`MealRow renders at most ${RENDER.mealRowUnrelatedRerendersMax}x extra on ${BUMPS} unrelated parent updates`, async () => {
    const extra = await countExtraRenders(MealRow, {
      row: MEAL_ROW_MODEL,
      foodLookup: EMPTY_FOOD_LOOKUP,
      onDeleteItem: NOOP,
      onEditItem: NOOP,
      onDeleteMeal: NOOP,
    });
    expect(
      extra,
      `MealRow's render ran ${extra} extra time(s) on ${BUMPS} unrelated parent updates. ` +
        `A memoized leaf with stable props should stay at 0.`,
    ).toBeLessThanOrEqual(RENDER.mealRowUnrelatedRerendersMax);
  });

  it(`FoodRow renders at most ${RENDER.foodRowUnrelatedRerendersMax}x extra on ${BUMPS} unrelated parent updates`, async () => {
    const extra = await countExtraRenders(FoodRow, {
      food: FOOD,
      onSelect: NOOP,
    });
    expect(
      extra,
      `FoodRow's render ran ${extra} extra time(s) on ${BUMPS} unrelated parent updates. ` +
        `A memoized leaf with stable props should stay at 0.`,
    ).toBeLessThanOrEqual(RENDER.foodRowUnrelatedRerendersMax);
  });
});
