"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

type ReadinessToday = components["schemas"]["ReadinessTodayResponse"];
type RecommendationList = components["schemas"]["RecommendationList"];
type DaySummary = components["schemas"]["DaySummaryResponse"];
type MealPlanTargets = components["schemas"]["MealPlanTargets"];
type ScheduledList = components["schemas"]["ScheduledWorkoutList"];

export function getReadinessToday(): Promise<ReadinessToday> {
  return api.get<ReadinessToday>("/v1/readiness/today");
}

export function listRecommendations(
  params: { limit?: number; cursor?: string } = {},
): Promise<RecommendationList> {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.cursor) q.set("cursor", params.cursor);
  const qs = q.toString();
  return api.get<RecommendationList>(`/v1/recommendations${qs ? `?${qs}` : ""}`);
}

export function getNutritionToday(date: string): Promise<DaySummary> {
  return api.get<DaySummary>(`/v1/nutrition/day?date=${encodeURIComponent(date)}`);
}

export function getNutritionTargets(): Promise<MealPlanTargets> {
  return api.get<MealPlanTargets>("/v1/nutrition/targets");
}

export function getScheduledRange(from: string, to: string): Promise<ScheduledList> {
  return api.get<ScheduledList>(
    `/v1/scheduled-workouts?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
  );
}

export type { ReadinessToday, RecommendationList, DaySummary, MealPlanTargets, ScheduledList };
