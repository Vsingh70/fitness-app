import { describe, expect, it } from "vitest";

import type { FoodResponse, PickedIngredient, Serving } from "@/lib/api/nutrition";
import {
  macrosForGrams,
  pickedToItemBody,
  resolveGrams,
  showsKcal,
  showsMacros,
} from "@/lib/nutrition/macros";

function makeServing(overrides: Partial<Serving> = {}): Serving {
  return {
    id: "serv-1",
    description: "1 cup",
    grams: "240",
    is_default: false,
    metric_amount: null,
    metric_unit: null,
    ...overrides,
  };
}

function makeFood(overrides: Partial<FoodResponse> = {}): FoodResponse {
  return {
    id: "food-1",
    name: "Oats",
    brand: null,
    archived_at: null,
    carbs_g_per_100g: "66",
    created_at: "2026-06-10T00:00:00Z",
    external_id: null,
    fat_g_per_100g: "7",
    fiber_g_per_100g: "10",
    kcal_per_100g: "380",
    owner_id: null,
    payload: {},
    protein_g_per_100g: "13",
    serving_label: null,
    serving_size_g: "40",
    servings: [],
    source: "user",
    ...overrides,
  };
}

describe("resolveGrams", () => {
  it("passes grams through unchanged for g and ml", () => {
    const food = makeFood();
    expect(resolveGrams(food, 150, "g", null)).toBe(150);
    expect(resolveGrams(food, 250, "ml", null)).toBe(250);
  });

  it("multiplies the serving weight by the amount for a named serving", () => {
    const food = makeFood();
    const cup = makeServing({ grams: "240" });
    // 2 cups * 240 g = 480 g
    expect(resolveGrams(food, 2, "serving", cup)).toBe(480);
    expect(resolveGrams(food, 0.5, "serving", cup)).toBe(120);
  });

  it("falls back to the food serving size then 100 g when serving grams are missing", () => {
    const food = makeFood({ serving_size_g: "30" });
    const noGrams = makeServing({ grams: null });
    expect(resolveGrams(food, 3, "serving", noGrams)).toBe(90);

    const bare = makeFood({ serving_size_g: null });
    expect(resolveGrams(bare, 2, "serving", noGrams)).toBe(200);
  });
});

describe("macrosForGrams + multi-ingredient totals", () => {
  it("scales per-100g macros by grams", () => {
    const food = makeFood();
    const m = macrosForGrams(food, 50);
    expect(m.kcal).toBeCloseTo(190, 5);
    expect(m.protein_g).toBeCloseTo(6.5, 5);
    expect(m.carbs_g).toBeCloseTo(33, 5);
    expect(m.fat_g).toBeCloseTo(3.5, 5);
  });

  it("sums correctly across three ingredients in different units", () => {
    const oats = makeFood({ id: "a", kcal_per_100g: "380", protein_g_per_100g: "13" });
    const milk = makeFood({ id: "b", kcal_per_100g: "50", protein_g_per_100g: "3.4" });
    const cup = makeServing({ grams: "240" });

    const ingredients: PickedIngredient[] = [
      { food: oats, amount: 80, unit: "g", serving: null, grams: 80 },
      {
        food: milk,
        amount: 1,
        unit: "serving",
        serving: cup,
        grams: resolveGrams(milk, 1, "serving", cup),
      },
      { food: oats, amount: 200, unit: "ml", serving: null, grams: 200 },
    ];

    const total = ingredients.reduce(
      (acc, ing) => {
        const m = macrosForGrams(ing.food, ing.grams);
        return { kcal: acc.kcal + m.kcal, protein: acc.protein + m.protein_g };
      },
      { kcal: 0, protein: 0 },
    );

    // oats 80g: 304 kcal; milk 240g: 120 kcal; oats 200ml(=200g): 760 kcal
    expect(total.kcal).toBeCloseTo(304 + 120 + 760, 4);
    // protein: oats 10.4 + milk 8.16 + oats 26 = 44.56
    expect(total.protein).toBeCloseTo(10.4 + 8.16 + 26, 4);
  });
});

describe("pickedToItemBody", () => {
  it("maps a gram pick to amount/unit with no serving id", () => {
    const food = makeFood();
    const body = pickedToItemBody({ food, amount: 120, unit: "g", serving: null, grams: 120 });
    expect(body).toEqual({ food_id: "food-1", amount: 120, unit: "g", serving_id: null });
  });

  it("includes the serving id only for serving units", () => {
    const food = makeFood();
    const cup = makeServing({ id: "cup-1" });
    const body = pickedToItemBody({ food, amount: 2, unit: "serving", serving: cup, grams: 480 });
    expect(body).toEqual({ food_id: "food-1", amount: 2, unit: "serving", serving_id: "cup-1" });
  });

  it("drops a stray serving id for ml picks", () => {
    const food = makeFood();
    const cup = makeServing({ id: "cup-1" });
    const body = pickedToItemBody({ food, amount: 250, unit: "ml", serving: cup, grams: 250 });
    expect(body.serving_id).toBeNull();
    expect(body.unit).toBe("ml");
  });
});

describe("tracking-mode display gating", () => {
  it("shows both for macros_and_calories", () => {
    expect(showsKcal("macros_and_calories")).toBe(true);
    expect(showsMacros("macros_and_calories")).toBe(true);
  });

  it("hides macros for calories_only", () => {
    expect(showsKcal("calories_only")).toBe(true);
    expect(showsMacros("calories_only")).toBe(false);
  });

  it("hides kcal for macros_only", () => {
    expect(showsKcal("macros_only")).toBe(false);
    expect(showsMacros("macros_only")).toBe(true);
  });
});
