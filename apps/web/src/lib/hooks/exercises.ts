"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/exercises";
import type { ListExerciseParams } from "@/lib/api/exercises";

export function useExercises(params: ListExerciseParams) {
  return useQuery({
    queryKey: ["exercises", params],
    queryFn: () => api.listExercises(params),
    staleTime: 5 * 60_000,
  });
}

export function useCreateExercise() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: api.ExerciseCreate) => api.createExercise(body),
    onSuccess: () => {
      // Refresh every exercise list (library + the workout picker's queries).
      qc.invalidateQueries({ queryKey: ["exercises"] });
    },
  });
}
