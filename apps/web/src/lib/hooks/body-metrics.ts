"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "@/lib/api/body-metrics";
import type { BodyMetricCreate, BodyMetricList } from "@/lib/api/body-metrics";

const BODY_METRICS_KEY = ["body-metrics"] as const;

export function useBodyMetrics(limit = 100) {
  return useQuery({
    queryKey: ["body-metrics", "list", limit] as const,
    queryFn: () => api.listBodyMetrics(limit),
    staleTime: 60_000,
  });
}

export function useBodyTrend(weeks = 12, window = 4) {
  return useQuery({
    queryKey: ["body-metrics", "trend", weeks, window] as const,
    queryFn: () => api.getBodyTrend(weeks, window),
    staleTime: 60_000,
  });
}

export function useLogBodyMetric() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BodyMetricCreate) => api.logBodyMetric(body),
    onMutate: async (body) => {
      await qc.cancelQueries({ queryKey: BODY_METRICS_KEY });
      const previous = qc.getQueriesData<BodyMetricList>({
        queryKey: ["body-metrics", "list"],
      });
      const now = new Date().toISOString();
      const optimistic = {
        id: `optimistic-${crypto.randomUUID()}`,
        recorded_at: body.recorded_at,
        created_at: now,
        weight_kg: body.weight_kg != null ? String(body.weight_kg) : null,
        body_fat_pct: body.body_fat_pct != null ? String(body.body_fat_pct) : null,
        neck_cm: null,
        waist_cm: null,
        hip_cm: null,
      };
      for (const [key, data] of previous) {
        if (!data) continue;
        qc.setQueryData<BodyMetricList>(key, { ...data, items: [optimistic, ...data.items] });
      }
      return { previous };
    },
    onError: (_err, _body, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: BODY_METRICS_KEY });
    },
  });
}

export function useDeleteBodyMetric() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteBodyMetric(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: BODY_METRICS_KEY });
      const previous = qc.getQueriesData<BodyMetricList>({
        queryKey: ["body-metrics", "list"],
      });
      for (const [key, data] of previous) {
        if (!data) continue;
        qc.setQueryData<BodyMetricList>(key, {
          ...data,
          items: data.items.filter((r) => r.id !== id),
        });
      }
      return { previous };
    },
    onError: (_err, _id, ctx) => {
      ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: BODY_METRICS_KEY });
    },
  });
}
