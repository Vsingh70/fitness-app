"use client";

import { v4 as uuidv4 } from "uuid";

import type {
  Exercise,
  ExerciseList,
  SetCreate,
  SetUpdate,
  WorkoutExercise,
  WorkoutSession,
  WorkoutSessionList,
  WorkoutSet,
} from "@/lib/workouts/types";
import type { ApiError } from "@/lib/api/client";

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface CallOpts {
  body?: unknown;
  idempotencyKey?: string;
}

async function call<T>(method: Method, path: string, opts: CallOpts = {}): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (opts.idempotencyKey) headers["Idempotency-Key"] = opts.idempotencyKey;
  const response = await fetch(`/api/proxy${path}`, {
    method,
    credentials: "include",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
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

export function newIdempotencyKey(): string {
  return uuidv4();
}

// Sessions ------------------------------------------------------------------

export const listSessions = (params: { limit?: number; cursor?: string } = {}) => {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.cursor) q.set("cursor", params.cursor);
  const qs = q.toString();
  return call<WorkoutSessionList>("GET", `/v1/workout-sessions${qs ? `?${qs}` : ""}`);
};

export const getSession = (id: string) => call<WorkoutSession>("GET", `/v1/workout-sessions/${id}`);

export const createSession = (body: { name?: string } = {}, idempotencyKey?: string) =>
  call<WorkoutSession>("POST", "/v1/workout-sessions", {
    body,
    idempotencyKey: idempotencyKey ?? newIdempotencyKey(),
  });

export const updateSession = (
  id: string,
  body: Partial<{
    name: string | null;
    notes: string | null;
    perceived_exertion: number | null;
    started_at: string;
    ended_at: string;
  }>,
) => call<WorkoutSession>("PATCH", `/v1/workout-sessions/${id}`, { body });

export const finishSession = (id: string) =>
  call<WorkoutSession>("POST", `/v1/workout-sessions/${id}/finish`);

export const deleteSession = (id: string) => call<void>("DELETE", `/v1/workout-sessions/${id}`);

export const restoreSession = (id: string) =>
  call<WorkoutSession>("POST", `/v1/workout-sessions/${id}/restore`);

// Workout exercises ---------------------------------------------------------

export const addExercise = (
  sessionId: string,
  body: { exercise_id: string; position?: number; notes?: string | null },
) => call<WorkoutExercise>("POST", `/v1/workout-sessions/${sessionId}/exercises`, { body });

export const reorderExercise = (workoutExerciseId: string, position: number) =>
  call<WorkoutExercise>("POST", `/v1/workout-exercises/${workoutExerciseId}/reorder`, {
    body: { position },
  });

export const removeExercise = (workoutExerciseId: string) =>
  call<void>("DELETE", `/v1/workout-exercises/${workoutExerciseId}`);

// Sets ----------------------------------------------------------------------

export const addSet = (workoutExerciseId: string, body: SetCreate, idempotencyKey?: string) =>
  call<WorkoutSet>("POST", `/v1/workout-exercises/${workoutExerciseId}/sets`, {
    body,
    idempotencyKey: idempotencyKey ?? newIdempotencyKey(),
  });

export const updateSet = (setId: string, body: SetUpdate) =>
  call<WorkoutSet>("PATCH", `/v1/sets/${setId}`, { body });

export const deleteSet = (setId: string) => call<void>("DELETE", `/v1/sets/${setId}`);

// Exercises (used by ExercisePicker) ----------------------------------------

export const searchExercises = (
  q?: string,
  opts: { mine_only?: boolean; limit?: number; cursor?: string } = {},
) => {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (opts.mine_only) params.set("mine_only", "true");
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.cursor) params.set("cursor", opts.cursor);
  const qs = params.toString();
  return call<ExerciseList>("GET", `/v1/exercises${qs ? `?${qs}` : ""}`);
};

export type { Exercise, WorkoutExercise, WorkoutSession, WorkoutSet };
