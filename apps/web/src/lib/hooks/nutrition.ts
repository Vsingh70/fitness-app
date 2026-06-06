"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/nutrition";

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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meals"] });
      qc.invalidateQueries({ queryKey: ["nutrition", "day"] });
    },
  });
}

export function useAddMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { mealId: string; body: api.MealItemCreate }) =>
      api.addMealItem(input.mealId, input.body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meals"] });
      qc.invalidateQueries({ queryKey: ["nutrition", "day"] });
    },
  });
}

export function useDeleteMealItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => api.deleteMealItem(itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meals"] });
      qc.invalidateQueries({ queryKey: ["nutrition", "day"] });
    },
  });
}

export function useDeleteMeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mealId: string) => api.deleteMeal(mealId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meals"] });
      qc.invalidateQueries({ queryKey: ["nutrition", "day"] });
    },
  });
}
