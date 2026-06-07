"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type BodyMetric = components["schemas"]["BodyMetricResponse"];
export type BodyMetricList = components["schemas"]["BodyMetricList"];
export type BodyMetricCreate = components["schemas"]["BodyMetricCreate"];
export type BodyMetricTrend = components["schemas"]["BodyMetricTrendResponse"];

export function listBodyMetrics(limit = 100): Promise<BodyMetricList> {
  const q = new URLSearchParams();
  q.set("limit", String(limit));
  return api.get<BodyMetricList>(`/v1/body-metrics?${q}`);
}

export function logBodyMetric(body: BodyMetricCreate): Promise<BodyMetric> {
  return api.post<BodyMetric>("/v1/body-metrics", body);
}

export function deleteBodyMetric(id: string): Promise<void> {
  return api.delete<void>(`/v1/body-metrics/${encodeURIComponent(id)}`);
}

export function getBodyTrend(weeks = 12, window = 4): Promise<BodyMetricTrend> {
  const q = new URLSearchParams();
  q.set("weeks", String(weeks));
  q.set("window", String(window));
  return api.get<BodyMetricTrend>(`/v1/body-metrics/trend?${q}`);
}
