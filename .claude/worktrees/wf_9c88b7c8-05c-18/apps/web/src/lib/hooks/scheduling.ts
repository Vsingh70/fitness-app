"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/scheduling";
import type { ScheduledWorkoutUpdate } from "@/lib/api/scheduling";

const KEY = (from?: string, to?: string) =>
  ["scheduled-workouts", { from: from ?? null, to: to ?? null }] as const;

export function useScheduledWorkouts(params: { from?: string; to?: string } = {}) {
  return useQuery({
    queryKey: KEY(params.from, params.to),
    queryFn: () => api.listScheduled(params),
    staleTime: 30_000,
  });
}

export function useUpdateScheduled() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      id: string;
      body: ScheduledWorkoutUpdate;
      shiftRemainingDays?: number;
    }) => api.patchScheduled(input.id, input.body, input.shiftRemainingDays ?? 0),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scheduled-workouts"] });
    },
  });
}

export function useStartScheduled() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.startScheduled(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scheduled-workouts"] });
      qc.invalidateQueries({ queryKey: ["workout-sessions"] });
    },
  });
}
