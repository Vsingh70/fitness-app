"use client";

import { useQuery } from "@tanstack/react-query";

import * as api from "@/lib/api/today";

export function useReadinessToday() {
  return useQuery({
    queryKey: ["readiness", "today"],
    queryFn: api.getReadinessToday,
    staleTime: 5 * 60_000,
  });
}

export function useRecommendations() {
  return useQuery({
    queryKey: ["recommendations"],
    queryFn: api.listRecommendations,
    staleTime: 60_000,
  });
}

export function useNutritionToday(isoDay: string) {
  return useQuery({
    queryKey: ["nutrition", "day", isoDay],
    queryFn: () => api.getNutritionToday(isoDay),
    staleTime: 30_000,
  });
}

export function useNutritionTargets() {
  return useQuery({
    queryKey: ["nutrition", "targets"],
    queryFn: api.getNutritionTargets,
    staleTime: 5 * 60_000,
  });
}

export function useScheduledRange(from: string, to: string) {
  return useQuery({
    queryKey: ["scheduled-workouts", "range", from, to],
    queryFn: () => api.getScheduledRange(from, to),
    staleTime: 30_000,
  });
}
