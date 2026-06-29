"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

// Plan shapes -------------------------------------------------------------
export type MealPlan = components["schemas"]["MealPlanResponse"];
export type MealPlanList = components["schemas"]["MealPlanList"];
export type MealPlanCreate = components["schemas"]["MealPlanCreate"];
export type MealPlanUpdate = components["schemas"]["MealPlanUpdate"];
export type MealPlanDay = components["schemas"]["MealPlanDayResponse"];
export type MealPlanDayCreate = components["schemas"]["MealPlanDayCreate"];
export type MealPlanDayPatch = components["schemas"]["MealPlanDayPatch"];
export type MealPlanMeal = components["schemas"]["MealPlanMealResponse"];
export type MealPlanMealCreate = components["schemas"]["MealPlanMealCreate"];
export type MealPlanMealPatch = components["schemas"]["MealPlanMealPatch"];
export type MealPlanItem = components["schemas"]["MealPlanItemResponse"];
export type MealPlanItemCreate = components["schemas"]["MealPlanItemCreate"];
export type MealPlanItemPatch = components["schemas"]["MealPlanItemPatch"];
export type MealPlanItemUnit = components["schemas"]["MealPlanItemUnit"];

export type PlanKind = components["schemas"]["MealPlanKind"];
export type ContentMode = components["schemas"]["MealPlanContentMode"];
export type TrackingMode = components["schemas"]["MealPlanTrackingMode"];
export type DayRole = components["schemas"]["MealPlanDayRole"];

export type ResolvedDay = components["schemas"]["ResolvedDay"];
export type ActivePlanProgress = components["schemas"]["ActivePlanProgress"];
export type PlanMacros = components["schemas"]["PlanMacros"];
export type PlanTargets = components["schemas"]["PlanTargets"];

// Labels ------------------------------------------------------------------
export const PLAN_KIND_LABEL: Record<PlanKind, string> = {
  daily_repeating: "Every day",
  training_rest: "Training and rest",
  weekly: "Weekly",
};

export const CONTENT_MODE_LABEL: Record<ContentMode, string> = {
  targets_only: "Targets only",
  meals_only: "Meals only",
  targets_and_meals: "Targets and meals",
};

export const TRACKING_MODE_LABEL: Record<TrackingMode, string> = {
  calories_only: "Calories only",
  macros_only: "Macros only",
  macros_and_calories: "Macros and calories",
};

/** Day-of-week labels indexed by dow (0 = Sunday, matching the backend). */
export const DOW_LABEL = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];
export const DOW_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function dayRoleLabel(role: DayRole): string {
  switch (role) {
    case "every_day":
      return "Every day";
    case "training":
      return "Training day";
    case "rest":
      return "Rest day";
    default: {
      const dow = Number(role.slice(4));
      return DOW_LABEL[dow] ?? role;
    }
  }
}

/** The day roles a plan of a given kind expects (in display order). */
export function dayRolesForKind(kind: PlanKind): DayRole[] {
  if (kind === "daily_repeating") return ["every_day"];
  if (kind === "training_rest") return ["training", "rest"];
  return ["dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"];
}

// Numeric helpers ---------------------------------------------------------
export function num(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const x = Number(value);
  return Number.isFinite(x) ? x : 0;
}

function macroLine(
  kcalRaw: string | number | null,
  proteinRaw: string | number | null,
  carbsRaw: string | number | null,
  fatRaw: string | number | null,
  tracking: TrackingMode,
): string {
  const kcal = `${Math.round(num(kcalRaw))} kcal`;
  const macros = `${Math.round(num(proteinRaw))}p · ${Math.round(num(carbsRaw))}c · ${Math.round(num(fatRaw))}f`;
  if (tracking === "calories_only") return kcal;
  if (tracking === "macros_only") return macros;
  return `${kcal} · ${macros}`;
}

/** Format a rolled-up PlanMacros (kcal/protein_g/...) per the plan's tracking mode. */
export function trackingLine(totals: PlanMacros, tracking: TrackingMode): string {
  return macroLine(totals.kcal, totals.protein_g, totals.carbs_g, totals.fat_g, tracking);
}

/** Format effective day targets (target_kcal/target_protein_g/...) per tracking mode. */
export function targetsLine(targets: PlanTargets, tracking: TrackingMode): string {
  return macroLine(
    targets.target_kcal,
    targets.target_protein_g,
    targets.target_carbs_g,
    targets.target_fat_g,
    tracking,
  );
}

// API: plans --------------------------------------------------------------
export function listMealPlans(
  params: { limit?: number; cursor?: string } = {},
): Promise<MealPlanList> {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.cursor) q.set("cursor", params.cursor);
  const qs = q.toString();
  return api.get<MealPlanList>(`/v1/meal-plans${qs ? `?${qs}` : ""}`);
}

export function getMealPlan(id: string): Promise<MealPlan> {
  return api.get<MealPlan>(`/v1/meal-plans/${id}`);
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

export function deactivateMealPlan(id: string): Promise<MealPlan> {
  return api.post<MealPlan>(`/v1/meal-plans/${id}/deactivate`);
}

export function getActivePlan(date?: string): Promise<ActivePlanProgress | null> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return api.get<ActivePlanProgress | null>(`/v1/meal-plans/active${q}`);
}

export function getPlanDay(planId: string, date: string): Promise<ResolvedDay> {
  const q = new URLSearchParams({ date });
  return api.get<ResolvedDay>(`/v1/meal-plans/${planId}/day?${q.toString()}`);
}

export type LoggedMeal = components["schemas"]["MealResponse"];

/** Materialize a planned meal into a logged meal for the given date (idempotent per slot+date). */
export function completePlannedMeal(
  planId: string,
  plannedMealId: string,
  date: string,
): Promise<LoggedMeal> {
  const q = new URLSearchParams({ date });
  return api.post<LoggedMeal>(
    `/v1/meal-plans/${planId}/meals/${plannedMealId}/complete?${q.toString()}`,
  );
}

// API: days ---------------------------------------------------------------
export function addPlanDay(planId: string, body: MealPlanDayCreate): Promise<MealPlanDay> {
  return api.post<MealPlanDay>(`/v1/meal-plans/${planId}/days`, body);
}

export function updatePlanDay(dayId: string, body: MealPlanDayPatch): Promise<MealPlanDay> {
  return api.patch<MealPlanDay>(`/v1/meal-plan-days/${dayId}`, body);
}

export function deletePlanDay(dayId: string): Promise<void> {
  return api.delete<void>(`/v1/meal-plan-days/${dayId}`);
}

// API: meals --------------------------------------------------------------
export function addPlanMeal(dayId: string, body: MealPlanMealCreate): Promise<MealPlanMeal> {
  return api.post<MealPlanMeal>(`/v1/meal-plan-days/${dayId}/meals`, body);
}

export function updatePlanMeal(mealId: string, body: MealPlanMealPatch): Promise<MealPlanMeal> {
  return api.patch<MealPlanMeal>(`/v1/meal-plan-meals/${mealId}`, body);
}

export function deletePlanMeal(mealId: string): Promise<void> {
  return api.delete<void>(`/v1/meal-plan-meals/${mealId}`);
}

// API: items --------------------------------------------------------------
export function addPlanItem(mealId: string, body: MealPlanItemCreate): Promise<MealPlanItem> {
  return api.post<MealPlanItem>(`/v1/meal-plan-meals/${mealId}/items`, body);
}

export function updatePlanItem(itemId: string, body: MealPlanItemPatch): Promise<MealPlanItem> {
  return api.patch<MealPlanItem>(`/v1/meal-plan-items/${itemId}`, body);
}

export function deletePlanItem(itemId: string): Promise<void> {
  return api.delete<void>(`/v1/meal-plan-items/${itemId}`);
}
