import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import type { MealItemResponse, MealList, MealResponse } from "@/lib/api/nutrition";
import {
  removeMealFromRanges,
  removeMealItemFromRanges,
  upsertMealInRanges,
  upsertMealItemInRanges,
} from "@/lib/hooks/nutrition";

const DAY_KEY = ["meals", "range", "2026-06-10T00:00:00Z", "2026-06-10T23:59:59Z"] as const;
const WEEK_KEY = ["meals", "range", "2026-06-08T00:00:00Z", "2026-06-14T23:59:59Z"] as const;

function makeItem(overrides: Partial<MealItemResponse> = {}): MealItemResponse {
  return {
    id: "item-1",
    meal_id: "meal-1",
    food_id: "food-1",
    amount: "100",
    unit: "g",
    serving_id: null,
    grams: "100",
    kcal: "380",
    protein_g: "13",
    carbs_g: "66",
    fat_g: "7",
    fiber_g: "10",
    created_at: "2026-06-10T08:00:00Z",
    ...overrides,
  };
}

function makeMeal(overrides: Partial<MealResponse> = {}): MealResponse {
  return {
    id: "meal-1",
    meal_type: "breakfast",
    name: null,
    eaten_at: "2026-06-10T08:00:00Z",
    notes: null,
    items: [],
    created_at: "2026-06-10T08:00:00Z",
    ...overrides,
  };
}

/** Seed a client with the day range and an overlapping week range. */
function seedClient(dayItems: MealResponse[], weekItems: MealResponse[] = dayItems): QueryClient {
  const qc = new QueryClient();
  qc.setQueryData<MealList>(DAY_KEY, { items: dayItems, next_cursor: null });
  qc.setQueryData<MealList>(WEEK_KEY, { items: weekItems, next_cursor: null });
  return qc;
}

function idsAt(qc: QueryClient, key: readonly unknown[]): string[] {
  return (qc.getQueryData<MealList>(key)?.items ?? []).map((m) => m.id);
}

describe("upsertMealInRanges", () => {
  it("inserts a new meal into every cached range containing its eaten_at", () => {
    const qc = seedClient([makeMeal()]);
    const lunch = makeMeal({ id: "meal-2", eaten_at: "2026-06-10T12:00:00Z" });

    upsertMealInRanges(qc, lunch);

    expect(idsAt(qc, DAY_KEY)).toEqual(["meal-1", "meal-2"]);
    expect(idsAt(qc, WEEK_KEY)).toEqual(["meal-1", "meal-2"]);
  });

  it("skips ranges that do not contain the meal", () => {
    const qc = seedClient([makeMeal()]);
    const friday = makeMeal({ id: "meal-2", eaten_at: "2026-06-12T12:00:00Z" });

    upsertMealInRanges(qc, friday);

    // Outside the day window, inside the week window.
    expect(idsAt(qc, DAY_KEY)).toEqual(["meal-1"]);
    expect(idsAt(qc, WEEK_KEY)).toEqual(["meal-1", "meal-2"]);
  });

  it("replaces an existing meal by id instead of appending", () => {
    const qc = seedClient([makeMeal({ notes: "old" })]);
    const updated = makeMeal({ notes: "new" });

    upsertMealInRanges(qc, updated);

    const day = qc.getQueryData<MealList>(DAY_KEY)!;
    expect(day.items).toHaveLength(1);
    expect(day.items[0]!.notes).toBe("new");
    expect(qc.getQueryData<MealList>(WEEK_KEY)!.items).toHaveLength(1);
  });

  it("evicts a meal from a range its new eaten_at no longer falls in", () => {
    const qc = seedClient([makeMeal()]);
    const moved = makeMeal({ eaten_at: "2026-06-12T08:00:00Z" });

    upsertMealInRanges(qc, moved);

    expect(idsAt(qc, DAY_KEY)).toEqual([]);
    expect(idsAt(qc, WEEK_KEY)).toEqual(["meal-1"]);
  });

  it("keeps items sorted by eaten_at with an id tiebreak (server order)", () => {
    const qc = seedClient([
      makeMeal({ id: "meal-b", eaten_at: "2026-06-10T08:00:00Z" }),
      makeMeal({ id: "meal-d", eaten_at: "2026-06-10T12:00:00Z" }),
    ]);

    // Same timestamp as meal-b: must land between by id, not by insertion order.
    upsertMealInRanges(qc, makeMeal({ id: "meal-c", eaten_at: "2026-06-10T08:00:00Z" }));
    upsertMealInRanges(qc, makeMeal({ id: "meal-a", eaten_at: "2026-06-10T08:00:00Z" }));

    expect(idsAt(qc, DAY_KEY)).toEqual(["meal-a", "meal-b", "meal-c", "meal-d"]);
  });
});

describe("upsertMealItemInRanges", () => {
  it("appends a new item to the owning meal in every range caching it", () => {
    const qc = seedClient([makeMeal({ items: [makeItem()] })]);
    const added = makeItem({ id: "item-2", food_id: "food-2" });

    upsertMealItemInRanges(qc, added);

    for (const key of [DAY_KEY, WEEK_KEY]) {
      const meal = qc.getQueryData<MealList>(key)!.items[0]!;
      expect(meal.items.map((i) => i.id)).toEqual(["item-1", "item-2"]);
    }
  });

  it("replaces an existing item by id", () => {
    const qc = seedClient([makeMeal({ items: [makeItem({ grams: "100" })] })]);

    upsertMealItemInRanges(qc, makeItem({ grams: "150" }));

    const meal = qc.getQueryData<MealList>(DAY_KEY)!.items[0]!;
    expect(meal.items).toHaveLength(1);
    expect(meal.items[0]!.grams).toBe("150");
  });

  it("reflects an item amount/unit edit (new grams + kcal) in every range", () => {
    const qc = seedClient([makeMeal({ items: [makeItem()] })]);

    // The server echoes the recomputed grams/kcal after a PATCH; the patch
    // helper must surface them so meal + day totals update immediately.
    upsertMealItemInRanges(
      qc,
      makeItem({ amount: "150", unit: "g", grams: "150", kcal: "570", protein_g: "20" }),
    );

    for (const key of [DAY_KEY, WEEK_KEY]) {
      const item = qc.getQueryData<MealList>(key)!.items[0]!.items[0]!;
      expect(item.amount).toBe("150");
      expect(item.grams).toBe("150");
      expect(item.kcal).toBe("570");
    }
  });

  it("leaves caches untouched when no range holds the owning meal", () => {
    const before = makeMeal();
    const qc = seedClient([before]);

    upsertMealItemInRanges(qc, makeItem({ meal_id: "meal-unknown" }));

    expect(qc.getQueryData<MealList>(DAY_KEY)!.items[0]).toEqual(before);
  });
});

describe("removeMealFromRanges", () => {
  it("removes the meal from every range and keeps the others", () => {
    const qc = seedClient([
      makeMeal(),
      makeMeal({ id: "meal-2", eaten_at: "2026-06-10T12:00:00Z" }),
    ]);

    removeMealFromRanges(qc, "meal-1");

    expect(idsAt(qc, DAY_KEY)).toEqual(["meal-2"]);
    expect(idsAt(qc, WEEK_KEY)).toEqual(["meal-2"]);
  });
});

describe("removeMealItemFromRanges", () => {
  it("removes the item from its meal in every range", () => {
    const meal = makeMeal({ items: [makeItem(), makeItem({ id: "item-2" })] });
    const qc = seedClient([meal]);

    removeMealItemFromRanges(qc, "item-1");

    for (const key of [DAY_KEY, WEEK_KEY]) {
      const cached = qc.getQueryData<MealList>(key)!.items[0]!;
      expect(cached.items.map((i) => i.id)).toEqual(["item-2"]);
    }
  });
});
