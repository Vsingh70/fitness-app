/**
 * Per-muscle weekly volume math. Primary muscle counts 1.0 set, secondary 0.5.
 * Pure helper, unit-testable.
 */

import type { components } from "@/lib/api/types";

export type Muscle = components["schemas"]["Muscle"];
type Exercise = components["schemas"]["ExerciseResponse"];
type Program = components["schemas"]["ProgramResponse"];

export interface VolumeEntry {
  muscle: Muscle;
  sets: number;
  /** "low" / "ok" / "high" against the goal range. */
  status: "low" | "ok" | "high";
}

export interface VolumeOptions {
  /** Lower bound of acceptable weekly sets per muscle. */
  min?: number;
  /** Upper bound. */
  max?: number;
}

const DEFAULT_MIN = 8;
const DEFAULT_MAX = 22;

export function computeVolume(
  program: Program,
  exercises: Map<string, Exercise>,
  options: VolumeOptions = {},
): VolumeEntry[] {
  const min = options.min ?? DEFAULT_MIN;
  const max = options.max ?? DEFAULT_MAX;
  const tally = new Map<Muscle, number>();

  for (const day of program.days) {
    for (const pde of day.exercises) {
      const ex = exercises.get(pde.exercise_id);
      if (!ex) continue;
      const primary = ex.primary_muscle;
      tally.set(primary, (tally.get(primary) ?? 0) + pde.target_sets * 1.0);
      const secondaries = ex.secondary_muscles ?? [];
      for (const m of secondaries) {
        tally.set(m, (tally.get(m) ?? 0) + pde.target_sets * 0.5);
      }
    }
  }

  return [...tally.entries()]
    .map(([muscle, sets]) => ({
      muscle,
      sets: Math.round(sets * 10) / 10,
      status: classify(sets, min, max),
    }))
    .sort((a, b) => b.sets - a.sets);
}

function classify(sets: number, min: number, max: number): "low" | "ok" | "high" {
  if (sets < min) return "low";
  if (sets > max) return "high";
  return "ok";
}
