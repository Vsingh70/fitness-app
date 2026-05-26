/**
 * Re-exports from the generated OpenAPI types, narrowed to the shapes the
 * workouts UI actually uses. Keeps call sites short.
 */

import type { components } from "@/lib/api/types";

export type WorkoutSession = components["schemas"]["WorkoutSessionResponse"];
export type WorkoutSessionListItem = components["schemas"]["WorkoutSessionListItem"];
export type WorkoutSessionList = components["schemas"]["WorkoutSessionList"];
export type WorkoutExercise = components["schemas"]["WorkoutExerciseResponse"];
export type WorkoutSet = components["schemas"]["SetResponse"];
export type SetCreate = components["schemas"]["SetCreate"];
export type SetUpdate = components["schemas"]["SetUpdate"];
export type SetType = components["schemas"]["SetType"];
export type TrackingType = components["schemas"]["TrackingType"];
export type Exercise = components["schemas"]["ExerciseResponse"];
export type ExerciseList = components["schemas"]["ExerciseList"];

/** Subset of `tracking_type` -> column definitions the UI renders. */
export const TRACKING_COLUMNS: Record<TrackingType, ReadonlyArray<keyof SetCreate>> = {
  weight_reps: ["weight_kg", "reps"],
  bodyweight_reps: ["reps", "weight_kg"],
  weighted_bodyweight: ["weight_kg", "reps"],
  time_only: ["duration_seconds"],
  weight_time: ["weight_kg", "duration_seconds"],
  distance_time: ["distance_meters", "duration_seconds"],
  weight_reps_distance: ["weight_kg", "reps", "distance_meters"],
  distance_time_pace: ["distance_meters", "duration_seconds"],
  cardio_machine: ["duration_seconds", "distance_meters"],
};

/** Fields required by tracking_type. Mirrors the API's validate_set_payload. */
export const TRACKING_REQUIRED: Record<TrackingType, ReadonlyArray<keyof SetCreate>> = {
  weight_reps: ["weight_kg", "reps"],
  bodyweight_reps: ["reps"],
  weighted_bodyweight: ["weight_kg", "reps"],
  time_only: ["duration_seconds"],
  weight_time: ["weight_kg", "duration_seconds"],
  distance_time: ["distance_meters", "duration_seconds"],
  weight_reps_distance: ["weight_kg", "reps", "distance_meters"],
  distance_time_pace: ["distance_meters", "duration_seconds"],
  cardio_machine: ["duration_seconds"],
};

export const SET_FIELD_LABEL: Record<keyof SetCreate, string> = {
  weight_kg: "kg",
  reps: "reps",
  duration_seconds: "time",
  distance_meters: "distance",
  rpe: "rpe",
  rir: "rir",
  notes: "notes",
  set_index: "set",
  set_type: "type",
};

export function validateSet(
  payload: Partial<Record<keyof SetCreate, unknown>>,
  trackingType: TrackingType,
): { ok: true } | { ok: false; reason: string } {
  const required = TRACKING_REQUIRED[trackingType];
  const allowed = TRACKING_COLUMNS[trackingType];
  const measurementProvided = (
    ["weight_kg", "reps", "duration_seconds", "distance_meters"] as const
  ).filter((k) => payload[k] !== undefined && payload[k] !== null && payload[k] !== "");
  const unexpected = measurementProvided.filter((k) => !allowed.includes(k));
  if (unexpected.length > 0) {
    return { ok: false, reason: `${unexpected.join(", ")} not valid for ${trackingType}` };
  }
  const missing = required.filter((k) => !measurementProvided.includes(k as never));
  if (missing.length > 0) {
    return { ok: false, reason: `${missing.join(", ")} required for ${trackingType}` };
  }
  return { ok: true };
}
