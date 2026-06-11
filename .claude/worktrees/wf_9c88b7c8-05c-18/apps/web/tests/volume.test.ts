import { describe, expect, it } from "vitest";

import { computeVolume } from "@/lib/programs/volume";
import type { components } from "@/lib/api/types";

type Exercise = components["schemas"]["ExerciseResponse"];
type Program = components["schemas"]["ProgramResponse"];

function makeExercise(id: string, primary: string, secondary: string[] = []): Exercise {
  return {
    id,
    slug: id,
    name: id,
    owner_id: null,
    primary_muscle: primary as Exercise["primary_muscle"],
    secondary_muscles: secondary as Exercise["secondary_muscles"],
    equipment: "barbell",
    movement_pattern: "horizontal_push",
    tracking_type: "weight_reps",
    is_unilateral: false,
    notes: null,
    cues: null,
    archived_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function makeProgram(exercises: { exerciseId: string; sets: number; dayIdx?: number }[]): Program {
  const days = new Map<number, Program["days"][number]>();
  for (const [i, ex] of exercises.entries()) {
    const dayIdx = ex.dayIdx ?? 0;
    if (!days.has(dayIdx)) {
      days.set(dayIdx, {
        id: `day-${dayIdx}`,
        day_index: dayIdx,
        name: `Day ${dayIdx}`,
        exercises: [],
      });
    }
    days.get(dayIdx)!.exercises.push({
      id: `pde-${i}`,
      exercise_id: ex.exerciseId,
      position: i,
      target_sets: ex.sets,
      target_reps_low: 5,
      target_reps_high: 10,
      target_rpe_low: null,
      target_rpe_high: null,
      target_rir_low: null,
      target_rir_high: null,
      rest_seconds: 90,
      progression_strategy: "none",
      notes: null,
    });
  }
  return {
    id: "p1",
    name: "Test",
    description: null,
    goal: "hypertrophy",
    weeks: 4,
    days_per_week: 4,
    source: "manual",
    template_id: null,
    is_active: false,
    activated_at: null,
    mesocycle_length_weeks: 4,
    auto_deload: true,
    days: [...days.values()].sort((a, b) => a.day_index - b.day_index),
    created_at: "2026-01-01T00:00:00Z",
  };
}

describe("computeVolume", () => {
  it("weights primary 1.0 and secondary 0.5", () => {
    const bench = makeExercise("bench", "chest", ["triceps", "front_delts"]);
    const exercises = new Map<string, Exercise>([["bench", bench]]);
    const program = makeProgram([{ exerciseId: "bench", sets: 4 }]);
    const result = computeVolume(program, exercises);
    expect(result.find((r) => r.muscle === "chest")?.sets).toBe(4);
    expect(result.find((r) => r.muscle === "triceps")?.sets).toBe(2);
    expect(result.find((r) => r.muscle === "front_delts")?.sets).toBe(2);
  });

  it("sums across multiple exercises and days", () => {
    const bench = makeExercise("bench", "chest", ["triceps"]);
    const incline = makeExercise("incline", "chest", ["front_delts"]);
    const exercises = new Map([
      ["bench", bench],
      ["incline", incline],
    ]);
    const program = makeProgram([
      { exerciseId: "bench", sets: 4, dayIdx: 0 },
      { exerciseId: "incline", sets: 3, dayIdx: 1 },
    ]);
    const result = computeVolume(program, exercises);
    expect(result.find((r) => r.muscle === "chest")?.sets).toBe(7);
    expect(result.find((r) => r.muscle === "triceps")?.sets).toBe(2);
    expect(result.find((r) => r.muscle === "front_delts")?.sets).toBe(1.5);
  });

  it("classifies under 8 as low, in [8,22] as ok, above 22 as high", () => {
    const bench = makeExercise("bench", "chest");
    const exercises = new Map([["bench", bench]]);

    const low = computeVolume(makeProgram([{ exerciseId: "bench", sets: 4 }]), exercises);
    expect(low[0]!.status).toBe("low");

    const ok = computeVolume(makeProgram([{ exerciseId: "bench", sets: 12 }]), exercises);
    expect(ok[0]!.status).toBe("ok");

    const high = computeVolume(makeProgram([{ exerciseId: "bench", sets: 25 }]), exercises);
    expect(high[0]!.status).toBe("high");
  });

  it("returns sorted descending by sets", () => {
    const bench = makeExercise("bench", "chest", ["triceps"]);
    const exercises = new Map([["bench", bench]]);
    const program = makeProgram([{ exerciseId: "bench", sets: 6 }]);
    const result = computeVolume(program, exercises);
    expect(result[0]!.muscle).toBe("chest"); // 6 > 3
    expect(result[1]!.muscle).toBe("triceps");
  });

  it("ignores exercises missing from the metadata map", () => {
    const program = makeProgram([{ exerciseId: "missing", sets: 4 }]);
    const result = computeVolume(program, new Map());
    expect(result).toEqual([]);
  });
});
