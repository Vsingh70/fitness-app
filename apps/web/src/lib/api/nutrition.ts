"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type FoodList = components["schemas"]["FoodList"];
export type FoodResponse = components["schemas"]["FoodResponse"];
export type FoodCreate = components["schemas"]["FoodCreate"];
export type Serving = components["schemas"]["FoodServingResponse"];
export type MealList = components["schemas"]["MealList"];
export type MealResponse = components["schemas"]["MealResponse"];
export type MealItemResponse = components["schemas"]["MealItemResponse"];
export type MealType = components["schemas"]["MealType"];
export type MealCreate = components["schemas"]["MealCreate"];
export type MealItemCreate = components["schemas"]["MealItemCreate"];
export type MealItemUpdate = components["schemas"]["MealItemUpdate"];
export type MealSwap = components["schemas"]["MealSwap"];
export type MealItemUnit = components["schemas"]["MealPlanItemUnit"];
export type DeleteScope = "today" | "forever";

/** A food chosen via the ingredient picker, with an amount/unit and resolved grams. */
export interface PickedIngredient {
  food: FoodResponse;
  amount: number;
  unit: MealItemUnit;
  /** Set when `unit === "serving"`. */
  serving: Serving | null;
  /** Resolved grams for the chosen amount/unit. */
  grams: number;
}

export function listMealsRange(fromIso: string, toIso: string): Promise<MealList> {
  const q = new URLSearchParams({ from: fromIso, to: toIso });
  return api.get<MealList>(`/v1/meals?${q.toString()}`);
}

export function createMeal(body: MealCreate): Promise<MealResponse> {
  return api.post<MealResponse>("/v1/meals", body);
}

export function addMealItem(mealId: string, body: MealItemCreate): Promise<MealItemResponse> {
  return api.post<MealItemResponse>(`/v1/meals/${mealId}/items`, body);
}

export function updateMealItem(itemId: string, body: MealItemUpdate): Promise<MealItemResponse> {
  return api.patch<MealItemResponse>(`/v1/meal-items/${itemId}`, body);
}

export function deleteMealItem(itemId: string): Promise<void> {
  return api.delete<void>(`/v1/meal-items/${itemId}`);
}

export function deleteMeal(mealId: string, scope: DeleteScope = "today"): Promise<void> {
  return api.delete<void>(`/v1/meals/${mealId}?scope=${scope}`);
}

/** Replace a logged meal's contents with another planned meal or a fresh item list. */
export function swapMeal(mealId: string, body: MealSwap): Promise<MealResponse> {
  return api.post<MealResponse>(`/v1/meals/${mealId}/swap`, body);
}

export function searchFoods(q: string, limit = 30): Promise<FoodList> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  return api.get<FoodList>(`/v1/foods/search?${params.toString()}`);
}

export function getFoodByBarcode(barcode: string): Promise<FoodResponse> {
  return api.get<FoodResponse>(`/v1/foods/barcode/${encodeURIComponent(barcode)}`);
}

export function getFood(foodId: string): Promise<FoodResponse> {
  return api.get<FoodResponse>(`/v1/foods/${foodId}`);
}

export function createFood(body: FoodCreate): Promise<FoodResponse> {
  return api.post<FoodResponse>("/v1/foods", body);
}
