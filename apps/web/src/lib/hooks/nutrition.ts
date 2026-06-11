"use client";

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as planApi from "@/lib/api/meal-plans";
import * as api from "@/lib/api/nutrition";

const MEALS_RANGE_KEY = ["meals", "range"] as const;

/** Ascending by (eaten_at, id) — matches the API's ordering for /v1/meals. */
function byEatenAt(a: api.MealResponse, b: api.MealResponse): number {
  const diff = new Date(a.eaten_at).getTime() - new Date(b.eaten_at).getTime();
  if (diff !== 0) return diff;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

function rangeOfKey(key: readonly unknown[]): { from: number; to: number } | null {
  const [, , from, to] = key;
  if (typeof from !== "string" || typeof to !== "string") return null;
  const fromMs = Date.parse(from);
  const toMs = Date.parse(to);
  return Number.isFinite(fromMs) && Number.isFinite(toMs) ? { from: fromMs, to: toMs } : null;
}

/** Insert or replace `meal` in every cached meals-range whose window contains it. */
export function upsertMealInRanges(qc: QueryClient, meal: api.MealResponse) {
  const eatenMs = new Date(meal.eaten_at).getTime();
  for (const [key, data] of qc.getQueriesData<api.MealList>({ queryKey: MEALS_RANGE_KEY })) {
    if (!data) continue;
    const range = rangeOfKey(key);
    const inRange = range !== null && eatenMs >= range.from && eatenMs <= range.to;
    const exists = data.items.some((m) => m.id === meal.id);
    if (!inRange && !exists) continue;
    const items = inRange
      ? [...data.items.filter((m) => m.id !== meal.id), meal].sort(byEatenAt)
      : data.items.filter((m) => m.id !== meal.id);
    qc.setQueryData(key, { ...data, items });
  }
}

/** Insert or replace a meal item inside whichever cached meal owns it. */
export function upsertMealItemInRanges(qc: QueryClient, item: api.MealItemResponse) {
  for (const [key, data] of qc.getQueriesData<api.MealList>({ queryKey: MEALS_RANGE_KEY })) {
    if (!data) continue;
    if (!data.items.some((m) => m.id === item.meal_id)) continue;
    qc.setQueryData(key, {
      ...data,
      items: data.items.map((meal) =>
        meal.id === item.meal_id
          ? {
              ...meal,
              items: meal.items.some((i) => i.id === item.id)
                ? meal.items.map((i) => (i.id === item.id ? item : i))
                : [...meal.items, item],
            }
          : meal,
      ),
    });
  }
}

export function removeMealItemFromRanges(qc: QueryClient, itemId: string) {
  for (const [key, data] of qc.getQueriesData<api.MealList>({ queryKey: MEALS_RANGE_KEY })) {
    if (!data) continue;
    if (!data.items.some((m) => m.items.some((i) => i.id === itemId))) continue;
    qc.setQueryData(key, {
      ...data,
      items: data.items.map((meal) => ({
        ...meal,
        items: meal.items.filter((i) => i.id !== itemId),
      })),
    });
  }
}

export function removeMealFromRanges(qc: QueryClient, mealId: string) {
  for (const [key, data] of qc.getQueriesData<api.MealList>({ queryKey: MEALS_RANGE_KEY })) {
    if (!data) continue;
    if (!data.items.some((m) => m.id === mealId)) continue;
    qc.setQueryData(key, { ...data, items: data.items.filter((m) => m.id !== mealId) });
  }
}

/**
 * Refetch the derived day queries a logging change affects: the day summary
 * (macro totals + adherence) and the active plan's consumed/remaining macros.
 * Scoped to `date` (ISO day) when the caller knows it; broad otherwise.
 */
function invalidateDaySummaries(qc: QueryClient, date?: string) {
  if (date) {
    qc.invalidateQueries({ queryKey: ["nutrition", "day", date] });
    qc.invalidateQueries({ queryKey: ["meal-plan", "active", date] });
  } else {
    qc.invalidateQueries({ queryKey: ["nutrition", "day"] });
    qc.invalidateQueries({ queryKey: ["meal-plan", "active"] });
  }
}

export function useMealsRange(fromIso: string, toIso: string) {
  return useQuery({
    queryKey: [...MEALS_RANGE_KEY, fromIso, toIso],
    // A day can exceed one page of meals; follow the cursor so the cached
    // range is complete (the patch helpers above rely on this exact shape).
    queryFn: async (): Promise<api.MealList> => {
      const items: api.MealResponse[] = [];
      let cursor: string | undefined;
      do {
        const page = await api.listMealsRange(fromIso, toIso, { limit: 100, cursor });
        items.push(...page.items);
        cursor = page.next_cursor ?? undefined;
      } while (cursor);
      return { items, next_cursor: null };
    },
    staleTime: 30_000,
  });
}

/** Most-recently/frequently logged foods, for the day screen's one-tap chips. */
export function useRecentFoods(limit = 12) {
  return useQuery({
    queryKey: ["foods", "recent", limit],
    queryFn: () => api.listRecentFoods(limit),
    staleTime: 60_000,
  });
}

export function useFoodSearch(query: string, enabled: boolean) {
  return useQuery({
    queryKey: ["food-search", query],
    queryFn: () => api.searchFoods(query, 25),
    enabled: enabled && query.trim().length >= 2,
    staleTime: 60_000,
  });
}

export function useCreateMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { body: api.MealCreate; date?: string }) => api.createMeal(input.body),
    onSuccess: (meal, { date }) => {
      upsertMealInRanges(qc, meal);
      invalidateDaySummaries(qc, date);
    },
  });
}

export function useAddMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { mealId: string; body: api.MealItemCreate; date?: string }) =>
      api.addMealItem(input.mealId, input.body),
    onSuccess: (item, { date }) => {
      upsertMealItemInRanges(qc, item);
      invalidateDaySummaries(qc, date);
    },
  });
}

export function useUpdateMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { itemId: string; body: api.MealItemUpdate; date?: string }) =>
      api.updateMealItem(input.itemId, input.body),
    onSuccess: (item, { date }) => {
      upsertMealItemInRanges(qc, item);
      invalidateDaySummaries(qc, date);
    },
  });
}

export function useDeleteMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { itemId: string; date?: string }) => api.deleteMealItem(input.itemId),
    onSuccess: (_res, { itemId, date }) => {
      removeMealItemFromRanges(qc, itemId);
      invalidateDaySummaries(qc, date);
    },
  });
}

export function useDeleteMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { mealId: string; scope: api.DeleteScope; date?: string }) =>
      api.deleteMeal(input.mealId, input.scope),
    onSuccess: (_res, { mealId, scope, date }) => {
      removeMealFromRanges(qc, mealId);
      invalidateDaySummaries(qc, date);
      // "forever" also removes the meal from the plan template itself.
      if (scope === "forever") {
        qc.invalidateQueries({ queryKey: ["meal-plans"] });
        qc.invalidateQueries({ queryKey: ["meal-plan"] });
      }
    },
  });
}

/** Materialize a planned meal into a logged meal for `date` (one tap "Mark complete"). */
export function useCompletePlannedMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { planId: string; plannedMealId: string; date: string }) =>
      planApi.completePlannedMeal(input.planId, input.plannedMealId, input.date),
    onSuccess: (meal, { date }) => {
      upsertMealInRanges(qc, meal);
      invalidateDaySummaries(qc, date);
    },
  });
}
