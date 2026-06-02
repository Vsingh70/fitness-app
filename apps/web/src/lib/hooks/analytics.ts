"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/analytics";
import type { InsightList } from "@/lib/api/analytics";

const INSIGHTS_KEY = ["insights", { dismissed: false }] as const;

export function useVolume(from: string, to: string) {
  return useQuery({
    queryKey: ["analytics", "volume", from, to],
    queryFn: () => api.getVolume(from, to),
    staleTime: 5 * 60_000,
  });
}

export function useCurrentWeekVolume() {
  return useQuery({
    queryKey: ["analytics", "volume", "current-week"],
    queryFn: api.getCurrentWeekVolume,
    staleTime: 60_000,
  });
}

export function useInsights() {
  return useQuery({
    queryKey: INSIGHTS_KEY,
    queryFn: () => api.listInsights({ dismissed: false }),
    staleTime: 60_000,
  });
}

/**
 * Optimistically remove a dismissed insight from the active list. The server
 * marks `dismissed_at`; on error we roll the card back.
 */
export function useDismissInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (insightId: string) => api.dismissInsight(insightId),
    onMutate: async (insightId) => {
      await qc.cancelQueries({ queryKey: INSIGHTS_KEY });
      const previous = qc.getQueryData<InsightList>(INSIGHTS_KEY);
      qc.setQueryData<InsightList>(INSIGHTS_KEY, (prev) =>
        prev ? { ...prev, items: prev.items.filter((i) => i.id !== insightId) } : prev,
      );
      return { previous };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) qc.setQueryData(INSIGHTS_KEY, ctx.previous);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}
