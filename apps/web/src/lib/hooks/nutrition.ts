"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as planApi from "@/lib/api/meal-plans";
import * as api from "@/lib/api/nutrition";

/** Invalidate every query a logging change can affect: meals, the day summary, and the active plan. */
function invalidateLogging(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["meals"] });
  qc.invalidateQueries({ queryKey: ["nutrition", "day"] });
  qc.invalidateQueries({ queryKey: ["meal-plan", "active"] });
}

export function useMealsRange(fromIso: string, toIso: string) {
  return useQuery({
    queryKey: ["meals", "range", fromIso, toIso],
    queryFn: () => api.listMealsRange(fromIso, toIso),
    staleTime: 30_000,
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
    mutationFn: (body: api.MealCreate) => api.createMeal(body),
    onSuccess: () => invalidateLogging(qc),
  });
}

export function useAddMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { mealId: string; body: api.MealItemCreate }) =>
      api.addMealItem(input.mealId, input.body),
    onSuccess: () => invalidateLogging(qc),
  });
}

export function useUpdateMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { itemId: string; body: api.MealItemUpdate }) =>
      api.updateMealItem(input.itemId, input.body),
    onSuccess: () => invalidateLogging(qc),
  });
}

export function useDeleteMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => api.deleteMealItem(itemId),
    onSuccess: () => invalidateLogging(qc),
  });
}

export function useDeleteMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { mealId: string; scope: api.DeleteScope }) =>
      api.deleteMeal(input.mealId, input.scope),
    onSuccess: () => invalidateLogging(qc),
  });
}

export function useSwapMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { mealId: string; body: api.MealSwap }) =>
      api.swapMeal(input.mealId, input.body),
    onSuccess: () => invalidateLogging(qc),
  });
}

/** Materialize a planned meal into a logged meal for `date` (one tap "Mark complete"). */
export function useCompletePlannedMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { planId: string; plannedMealId: string; date: string }) =>
      planApi.completePlannedMeal(input.planId, input.plannedMealId, input.date),
    onSuccess: () => invalidateLogging(qc),
  });
}
