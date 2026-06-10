"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/meal-plans";
import type {
  MealPlanCreate,
  MealPlanDayCreate,
  MealPlanDayPatch,
  MealPlanItemCreate,
  MealPlanItemPatch,
  MealPlanMealCreate,
  MealPlanMealPatch,
  MealPlanUpdate,
} from "@/lib/api/meal-plans";

const KEY = ["meal-plans"] as const;
const PLAN_KEY = (id: string) => ["meal-plan", id] as const;

export function useMealPlans() {
  return useQuery({
    queryKey: KEY,
    queryFn: api.listMealPlans,
    staleTime: 60_000,
  });
}

export function useMealPlan(id: string | null | undefined) {
  return useQuery({
    queryKey: PLAN_KEY(id ?? "none"),
    queryFn: () => api.getMealPlan(id as string),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useActivePlan(date?: string) {
  return useQuery({
    queryKey: ["meal-plan", "active", date ?? "today"],
    queryFn: () => api.getActivePlan(date),
    staleTime: 30_000,
  });
}

function invalidatePlan(qc: ReturnType<typeof useQueryClient>, id?: string) {
  qc.invalidateQueries({ queryKey: KEY });
  if (id) qc.invalidateQueries({ queryKey: PLAN_KEY(id) });
  qc.invalidateQueries({ queryKey: ["meal-plan", "active"] });
  // Activating/editing a plan changes the derived nutrition targets.
  qc.invalidateQueries({ queryKey: ["nutrition"] });
  qc.invalidateQueries({ queryKey: ["nutrition.targets"] });
}

// Plan-level --------------------------------------------------------------
export function useCreateMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MealPlanCreate) => api.createMealPlan(body),
    onSuccess: (plan) => invalidatePlan(qc, plan.id),
  });
}

export function useUpdateMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: MealPlanUpdate }) =>
      api.updateMealPlan(id, body),
    onSuccess: (plan) => invalidatePlan(qc, plan.id),
  });
}

export function useDeleteMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteMealPlan(id),
    onSuccess: () => invalidatePlan(qc),
  });
}

export function useActivateMealPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.activateMealPlan(id),
    onSuccess: (plan) => invalidatePlan(qc, plan.id),
  });
}

// Day-level ---------------------------------------------------------------
export function useAddPlanDay(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: MealPlanDayCreate) => api.addPlanDay(planId, body),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

export function useUpdatePlanDay(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ dayId, body }: { dayId: string; body: MealPlanDayPatch }) =>
      api.updatePlanDay(dayId, body),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

export function useDeletePlanDay(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dayId: string) => api.deletePlanDay(dayId),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

// Meal-level --------------------------------------------------------------
export function useAddPlanMeal(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ dayId, body }: { dayId: string; body: MealPlanMealCreate }) =>
      api.addPlanMeal(dayId, body),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

export function useUpdatePlanMeal(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mealId, body }: { mealId: string; body: MealPlanMealPatch }) =>
      api.updatePlanMeal(mealId, body),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

export function useDeletePlanMeal(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mealId: string) => api.deletePlanMeal(mealId),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

// Item-level --------------------------------------------------------------
export function useAddPlanItem(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mealId, body }: { mealId: string; body: MealPlanItemCreate }) =>
      api.addPlanItem(mealId, body),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

export function useUpdatePlanItem(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, body }: { itemId: string; body: MealPlanItemPatch }) =>
      api.updatePlanItem(itemId, body),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}

export function useDeletePlanItem(planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => api.deletePlanItem(itemId),
    onSuccess: () => invalidatePlan(qc, planId),
  });
}
