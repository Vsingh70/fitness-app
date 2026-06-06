"use client";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/types";

export type Exercise = components["schemas"]["ExerciseResponse"];
export type ExerciseList = components["schemas"]["ExerciseList"];
export type ExerciseCreate = components["schemas"]["ExerciseCreate"];

export type Muscle = components["schemas"]["Muscle"];
export type Equipment = components["schemas"]["Equipment"];
export type MovementPattern = components["schemas"]["MovementPattern"];
export type TrackingType = components["schemas"]["TrackingType"];

// Enum value lists for filter chips + the create form. Kept in display order.
export const MUSCLES: Muscle[] = [
  "chest",
  "lats",
  "traps",
  "rhomboids",
  "rear_delts",
  "side_delts",
  "front_delts",
  "biceps",
  "triceps",
  "forearms",
  "abs",
  "obliques",
  "lower_back",
  "glutes",
  "quads",
  "hamstrings",
  "adductors",
  "abductors",
  "calves",
];

export const EQUIPMENT: Equipment[] = [
  "barbell",
  "dumbbell",
  "cable",
  "machine",
  "bodyweight",
  "banded",
  "kettlebell",
  "smith_machine",
  "trap_bar",
  "ez_bar",
  "plate_loaded",
  "cardio_machine",
  "other",
];

export const MOVEMENT_PATTERNS: MovementPattern[] = [
  "squat",
  "hinge",
  "horizontal_push",
  "vertical_push",
  "horizontal_pull",
  "vertical_pull",
  "lunge",
  "carry",
  "rotation",
  "anti_rotation",
  "isolation",
  "cardio",
];

export const TRACKING_TYPES: TrackingType[] = [
  "weight_reps",
  "weight_reps_distance",
  "weight_time",
  "bodyweight_reps",
  "weighted_bodyweight",
  "time_only",
  "distance_time",
  "distance_time_pace",
  "cardio_machine",
];

/** snake_case enum value -> "Title Case" label for display. */
export function labelize(value: string): string {
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export interface ListExerciseParams {
  q?: string;
  muscle?: Muscle;
  equipment?: Equipment;
  movement_pattern?: MovementPattern;
  mine_only?: boolean;
  limit?: number;
  cursor?: string;
}

export function listExercises(params: ListExerciseParams = {}): Promise<ExerciseList> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.muscle) qs.set("muscle", params.muscle);
  if (params.equipment) qs.set("equipment", params.equipment);
  if (params.movement_pattern) qs.set("movement_pattern", params.movement_pattern);
  if (params.mine_only) qs.set("mine_only", "true");
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.cursor) qs.set("cursor", params.cursor);
  const s = qs.toString();
  return api.get<ExerciseList>(`/v1/exercises${s ? `?${s}` : ""}`);
}

export function createExercise(body: ExerciseCreate): Promise<Exercise> {
  return api.post<Exercise>("/v1/exercises", body);
}
