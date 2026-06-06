"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type MealPlan = components["schemas"]["MealPlanResponse"];
export type MealPlanList = components["schemas"]["MealPlanList"];
export type MealPlanCreate = components["schemas"]["MealPlanCreate"];
export type MealPlanUpdate = components["schemas"]["MealPlanUpdate"];

// ---------------------------------------------------------------------------
// `days` JSONB shape (owned by the frontend — the backend stores it opaquely).
// One shape covers all three day structures and both meal-content modes:
//  - a planned meal may carry MANUAL macros and/or LINKED food items;
//    when items are present their macros are summed, else the manual values
//    are used.
// ---------------------------------------------------------------------------

export type DayStructure = "weekdays" | "day_types" | "single";

export interface PlannedItem {
  food_id: string;
  name: string;
  grams: number;
  // per-100g macros captured at link time so totals don't need a re-fetch
  kcal_per_100g: number;
  protein_g_per_100g: number;
  carbs_g_per_100g: number;
  fat_g_per_100g: number;
}

export interface PlannedMeal {
  label: string;
  // manual macros (used when there are no linked items)
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  items: PlannedItem[];
}

export interface PlannedDay {
  key: string; // e.g. "monday" | "training" | "every_day"
  label: string;
  meals: PlannedMeal[];
}

export interface PlanDays {
  structure: DayStructure;
  days: PlannedDay[];
}

export const WEEKDAYS: { key: string; label: string }[] = [
  { key: "monday", label: "Monday" },
  { key: "tuesday", label: "Tuesday" },
  { key: "wednesday", label: "Wednesday" },
  { key: "thursday", label: "Thursday" },
  { key: "friday", label: "Friday" },
  { key: "saturday", label: "Saturday" },
  { key: "sunday", label: "Sunday" },
];

export function emptyDays(structure: DayStructure): PlanDays {
  if (structure === "single") {
    return { structure, days: [{ key: "every_day", label: "Every day", meals: [] }] };
  }
  if (structure === "weekdays") {
    return { structure, days: WEEKDAYS.map((d) => ({ ...d, meals: [] })) };
  }
  // day_types: start with Training + Rest, user can rename/add
  return {
    structure,
    days: [
      { key: "training", label: "Training day", meals: [] },
      { key: "rest", label: "Rest day", meals: [] },
    ],
  };
}

/** Coerce arbitrary stored JSONB into a valid PlanDays (older/empty plans). */
export function parseDays(raw: unknown): PlanDays {
  const obj = (raw ?? {}) as Partial<PlanDays>;
  const structure: DayStructure =
    obj.structure === "weekdays" || obj.structure === "day_types" || obj.structure === "single"
      ? obj.structure
      : "single";
  if (!Array.isArray(obj.days) || obj.days.length === 0) return emptyDays(structure);
  return { structure, days: obj.days as PlannedDay[] };
}

export interface Macros {
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

/** Macros for one planned meal: sum of linked items if any, else manual values. */
export function mealMacros(meal: PlannedMeal): Macros {
  if (meal.items.length > 0) {
    return meal.items.reduce<Macros>(
      (acc, it) => {
        const f = it.grams / 100;
        return {
          kcal: acc.kcal + it.kcal_per_100g * f,
          protein_g: acc.protein_g + it.protein_g_per_100g * f,
          carbs_g: acc.carbs_g + it.carbs_g_per_100g * f,
          fat_g: acc.fat_g + it.fat_g_per_100g * f,
        };
      },
      { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
    );
  }
  return { kcal: meal.kcal, protein_g: meal.protein_g, carbs_g: meal.carbs_g, fat_g: meal.fat_g };
}

export function dayMacros(day: PlannedDay): Macros {
  return day.meals.reduce<Macros>(
    (acc, m) => {
      const mm = mealMacros(m);
      return {
        kcal: acc.kcal + mm.kcal,
        protein_g: acc.protein_g + mm.protein_g,
        carbs_g: acc.carbs_g + mm.carbs_g,
        fat_g: acc.fat_g + mm.fat_g,
      };
    },
    { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
  );
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export function listMealPlans(): Promise<MealPlanList> {
  return api.get<MealPlanList>("/v1/meal-plans");
}

export function createMealPlan(body: MealPlanCreate): Promise<MealPlan> {
  return api.post<MealPlan>("/v1/meal-plans", body);
}

export function updateMealPlan(id: string, body: MealPlanUpdate): Promise<MealPlan> {
  return api.patch<MealPlan>(`/v1/meal-plans/${id}`, body);
}

export function deleteMealPlan(id: string): Promise<void> {
  return api.delete<void>(`/v1/meal-plans/${id}`);
}

export function activateMealPlan(id: string): Promise<MealPlan> {
  return api.post<MealPlan>(`/v1/meal-plans/${id}/activate`);
}
