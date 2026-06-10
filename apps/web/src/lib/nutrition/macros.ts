import { num } from "@/lib/api/meal-plans";
import type { TrackingMode } from "@/lib/api/meal-plans";
import type { FoodResponse, MealItemCreate, PickedIngredient, Serving } from "@/lib/api/nutrition";

export interface Macros {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

/** Whether the kcal ring/figure should be shown for a given tracking mode. */
export function showsKcal(mode: TrackingMode): boolean {
  return mode !== "macros_only";
}

/** Whether the protein/carbs/fat bars should be shown for a given tracking mode. */
export function showsMacros(mode: TrackingMode): boolean {
  return mode !== "calories_only";
}

/** Convert a picked ingredient into a logged-item body the server resolves to grams/macros. */
export function pickedToItemBody(picked: PickedIngredient): MealItemCreate {
  return {
    food_id: picked.food.id,
    amount: picked.amount,
    unit: picked.unit,
    serving_id: picked.unit === "serving" ? (picked.serving?.id ?? null) : null,
  };
}

/**
 * Resolve a chosen amount + unit on a food to grams. For `g`/`ml` the amount is
 * already in grams (we treat ml as 1:1 for density, matching the backend). For
 * a named serving the amount is the count of that serving, multiplied by its
 * gram weight.
 */
export function resolveGrams(
  food: FoodResponse,
  amount: number,
  unit: "g" | "ml" | "serving",
  serving: Serving | null,
): number {
  if (unit === "serving" && serving) {
    const per = num(serving.grams) || num(food.serving_size_g) || 100;
    return amount * per;
  }
  return amount;
}

/** Macros for a given gram weight of a food, from its per-100g values. */
export function macrosForGrams(food: FoodResponse, grams: number): Macros {
  const f = grams / 100;
  return {
    kcal: num(food.kcal_per_100g) * f,
    protein_g: num(food.protein_g_per_100g) * f,
    carbs_g: num(food.carbs_g_per_100g) * f,
    fat_g: num(food.fat_g_per_100g) * f,
  };
}

/** Short macro summary like "320 kcal · 24p · 30c · 12f". */
export function macroSummary(m: Macros): string {
  return `${Math.round(m.kcal)} kcal · ${Math.round(m.protein_g)}p · ${Math.round(m.carbs_g)}c · ${Math.round(m.fat_g)}f`;
}
