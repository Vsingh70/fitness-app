"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/meal-plans";
import type { MealPlanCreate, MealPlanUpdate } from "@/lib/api/meal-plans";

const KEY = ["meal-plans"] as const;

export function useMealPlans() {
  return useQuery({
    queryKey: KEY,
    queryFn: api.listMealPlans,
    staleTime: 60_000,
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: KEY });
  // Activating/editing a plan changes the derived nutrition targets.
  qc.invalidateQueries({ queryKey: ["nutrition"] });
  qc.invalidateQueries({ queryKey: ["nutrition.targets"] });
}

export function useCreateMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MealPlanCreate) => api.createMealPlan(body),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: MealPlanUpdate }) =>
      api.updateMealPlan(id, body),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteMealPlan(id),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useActivateMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.activateMealPlan(id),
    onSuccess: () => invalidateAll(qc),
  });
}
