"use client";

import type { ApiError } from "@/lib/api/client";
import { reschedulePathSuffix } from "@/lib/scheduling/chip";
import type { components } from "@/lib/api/types";

type ScheduledWorkoutList = components["schemas"]["ScheduledWorkoutList"];
type ScheduledWorkoutWithDay = components["schemas"]["ScheduledWorkoutWithDay"];
type ScheduledWorkoutUpdate = components["schemas"]["ScheduledWorkoutUpdate"];
type WorkoutSession = components["schemas"]["WorkoutSessionResponse"];

async function call<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    method,
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const payload: unknown = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const err = (payload as { error?: { code?: string; message?: string; details?: unknown } })
      ?.error;
    const apiError: ApiError = {
      status: response.status,
      code: err?.code ?? "internal_error",
      message: err?.message ?? `Request failed with ${response.status}`,
      details: err?.details,
    };
    throw apiError;
  }
  return payload as T;
}

export function listScheduled(
  params: { from?: string; to?: string } = {},
): Promise<ScheduledWorkoutList> {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  const qs = q.toString();
  return call<ScheduledWorkoutList>("GET", `/v1/scheduled-workouts${qs ? `?${qs}` : ""}`);
}

export function patchScheduled(
  id: string,
  body: ScheduledWorkoutUpdate,
  shiftRemainingDays = 0,
): Promise<ScheduledWorkoutWithDay> {
  return call<ScheduledWorkoutWithDay>(
    "PATCH",
    `/v1/scheduled-workouts/${id}${reschedulePathSuffix(shiftRemainingDays)}`,
    body,
  );
}

export function startScheduled(id: string): Promise<WorkoutSession> {
  return call<WorkoutSession>("POST", `/v1/scheduled-workouts/${id}/start`);
}

export type { ScheduledWorkoutList, ScheduledWorkoutWithDay, ScheduledWorkoutUpdate };
