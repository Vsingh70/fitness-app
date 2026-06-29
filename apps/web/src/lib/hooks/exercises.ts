"use client";

import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useMemo } from "react";

import * as api from "@/lib/api/exercises";
import type { Exercise, ListExerciseParams } from "@/lib/api/exercises";

export function useExercises(params: ListExerciseParams) {
  return useQuery({
    queryKey: ["exercises", params],
    queryFn: () => api.listExercises(params),
    staleTime: 5 * 60_000,
  });
}

/**
 * Paginated exercise list. The catalogue runs to hundreds of entries, so the
 * library pages through the cursor (`next_cursor`) rather than capping at the
 * first page. A search `q` orders by similarity and returns a null cursor, so
 * it collapses to a single page.
 */
export function useInfiniteExercises(params: ListExerciseParams) {
  return useInfiniteQuery({
    queryKey: ["exercises", "infinite", params],
    queryFn: ({ pageParam }) => api.listExercises({ ...params, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}

/** Fetch metadata for a specific set of exercises, keyed by the sorted id list. */
export function useExerciseMeta(exerciseIds: string[]) {
  const ids = useMemo(() => [...new Set(exerciseIds)].sort(), [exerciseIds]);
  return useQuery({
    queryKey: ["exercise-meta", ids],
    queryFn: async () => {
      const map = new Map<string, Exercise>();
      if (ids.length === 0) return map;
      const list = await api.listExercises({ ids });
      for (const ex of list.items) map.set(ex.id, ex);
      return map;
    },
    enabled: ids.length > 0,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
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
