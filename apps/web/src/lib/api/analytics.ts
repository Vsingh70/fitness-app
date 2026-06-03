"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

type VolumeResponse = components["schemas"]["VolumeResponse"];
type CurrentWeekResponse = components["schemas"]["CurrentWeekResponse"];
type InsightList = components["schemas"]["InsightList"];
type InsightResponse = components["schemas"]["InsightResponse"];
type InsightSeverity = components["schemas"]["AnalyticsInsightSeverity"];
type InsightKind = components["schemas"]["AnalyticsInsightKind"];

export type ExerciseAnalytics = components["schemas"]["ExerciseAnalyticsResponse"];

/** Per-exercise analytics for the exercise detail page. */
export function getExerciseAnalytics(
  exerciseId: string,
  window: string = "12w",
): Promise<ExerciseAnalytics> {
  return api.get<ExerciseAnalytics>(
    `/v1/analytics/exercises/${encodeURIComponent(exerciseId)}?window=${encodeURIComponent(window)}`,
  );
}

/** Weekly per-muscle volume series. `from`/`to` are ISO dates (YYYY-MM-DD). */
export function getVolume(from: string, to: string): Promise<VolumeResponse> {
  return api.get<VolumeResponse>(
    `/v1/analytics/volume?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
  );
}

/** Current-week per-muscle summary used by the heatmap. */
export function getCurrentWeekVolume(): Promise<CurrentWeekResponse> {
  return api.get<CurrentWeekResponse>("/v1/analytics/volume/current-week");
}

export interface ListInsightsParams {
  dismissed?: boolean;
  kind?: InsightKind;
  severity?: InsightSeverity;
  limit?: number;
  cursor?: string;
}

export function listInsights(params: ListInsightsParams = {}): Promise<InsightList> {
  const q = new URLSearchParams();
  if (params.dismissed !== undefined) q.set("dismissed", String(params.dismissed));
  if (params.kind) q.set("kind", params.kind);
  if (params.severity) q.set("severity", params.severity);
  if (params.limit !== undefined) q.set("limit", String(params.limit));
  if (params.cursor) q.set("cursor", params.cursor);
  const qs = q.toString();
  return api.get<InsightList>(`/v1/insights${qs ? `?${qs}` : ""}`);
}

/**
 * Dismiss an insight. The generated spec exposes this as
 * `POST /v1/insights/{id}/dismiss` (the task referenced a PATCH variant which
 * does not exist). Returns the updated insight with `dismissed_at` set.
 */
export function dismissInsight(insightId: string): Promise<InsightResponse> {
  return api.post<InsightResponse>(`/v1/insights/${encodeURIComponent(insightId)}/dismiss`);
}

export type {
  VolumeResponse,
  CurrentWeekResponse,
  InsightList,
  InsightResponse,
  InsightSeverity,
  InsightKind,
};
