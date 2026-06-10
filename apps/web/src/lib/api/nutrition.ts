"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type FoodList = components["schemas"]["FoodList"];
export type FoodResponse = components["schemas"]["FoodResponse"];
export type Serving = components["schemas"]["FoodServingResponse"];
export type MealList = components["schemas"]["MealList"];
export type MealResponse = components["schemas"]["MealResponse"];
export type MealItemResponse = components["schemas"]["MealItemResponse"];
export type MealType = components["schemas"]["MealType"];
export type MealCreate = components["schemas"]["MealCreate"];
export type MealItemCreate = components["schemas"]["MealItemCreate"];

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

export function deleteMealItem(itemId: string): Promise<void> {
  return api.delete<void>(`/v1/meal-items/${itemId}`);
}

export function deleteMeal(mealId: string): Promise<void> {
  return api.delete<void>(`/v1/meals/${mealId}`);
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
