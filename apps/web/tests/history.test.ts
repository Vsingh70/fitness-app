import { describe, expect, it } from "vitest";

import {
  bestE1RMByDay,
  epleyE1RM,
  filterSessionsByRange,
  groupByWeek,
  isoDayInTz,
  rollupSession,
  volumeByDay,
} from "@/lib/workouts/history";
import type { WorkoutExercise, WorkoutSession, WorkoutSet } from "@/lib/workouts/types";

function makeSet(overrides: Partial<WorkoutSet> = {}): WorkoutSet {
  return {
    id: "set",
    set_index: 0,
    set_type: "working",
    weight_kg: null,
    reps: null,
    duration_seconds: null,
    distance_meters: null,
    rpe: null,
    rir: null,
    rounds: null,
    segments: [],
    is_pr: false,
    notes: null,
    ...overrides,
  };
}

function makeWe(overrides: Partial<WorkoutExercise> = {}): WorkoutExercise {
  return {
    id: "we",
    exercise_id: "bench",
    exercise_name: "Bench Press",
    tracking_type: "weight_reps",
    position: 0,
    notes: null,
    block_kind: "working",
    block_label: null,
    substituted_for_exercise_id: null,
    sets: [],
    ...overrides,
  };
}

function makeSession(overrides: Partial<WorkoutSession> = {}): WorkoutSession {
  return {
    id: "s1",
    name: null,
    scheduled_workout_id: null,
    started_at: "2026-05-20T10:00:00Z",
    ended_at: "2026-05-20T11:00:00Z",
    notes: null,
    bodyweight_kg: null,
    perceived_exertion: null,
    workout_exercises: [],
    ...overrides,
  };
}

describe("epleyE1RM", () => {
  it("matches Epley formula", () => {
    expect(epleyE1RM(100, 5)).toBeCloseTo(116.666, 2);
    expect(epleyE1RM(150, 1)).toBeCloseTo(155, 2);
  });

  it("returns 0 for non-positive inputs", () => {
    expect(epleyE1RM(0, 5)).toBe(0);
    expect(epleyE1RM(100, 0)).toBe(0);
    expect(epleyE1RM(100, -2)).toBe(0);
  });
});

describe("filterSessionsByRange", () => {
  const now = new Date("2026-05-25T00:00:00Z").getTime();
  const within4w = makeSession({ id: "a", started_at: "2026-05-10T00:00:00Z" });
  const within12w = makeSession({ id: "b", started_at: "2026-03-15T00:00:00Z" });
  const within1y = makeSession({ id: "c", started_at: "2025-09-01T00:00:00Z" });
  const old = makeSession({ id: "d", started_at: "2023-01-01T00:00:00Z" });

  it("returns everything for all", () => {
    expect(filterSessionsByRange([within4w, within12w, within1y, old], "all", now)).toHaveLength(4);
  });

  it("filters by 4w", () => {
    const out = filterSessionsByRange([within4w, within12w, within1y, old], "4w", now);
    expect(out.map((s) => s.id)).toEqual(["a"]);
  });

  it("filters by 12w", () => {
    const out = filterSessionsByRange([within4w, within12w, within1y, old], "12w", now);
    expect(out.map((s) => s.id).sort()).toEqual(["a", "b"]);
  });

  it("filters by 1y", () => {
    const out = filterSessionsByRange([within4w, within12w, within1y, old], "1y", now);
    expect(out.map((s) => s.id).sort()).toEqual(["a", "b", "c"]);
  });
});

describe("isoDayInTz", () => {
  it("respects timezone offset across midnight", () => {
    // 2026-05-21T05:00:00Z is 2026-05-21 in UTC but 2026-05-20 in America/New_York (UTC-4 in May).
    expect(isoDayInTz("2026-05-21T05:00:00Z", "UTC")).toBe("2026-05-21");
    expect(isoDayInTz("2026-05-21T05:00:00Z", "America/New_York")).toBe("2026-05-21");
    // 03:00Z in NY is the previous day
    expect(isoDayInTz("2026-05-21T03:00:00Z", "America/New_York")).toBe("2026-05-20");
  });
});

describe("bestE1RMByDay + volumeByDay", () => {
  const sessions: WorkoutSession[] = [
    makeSession({
      id: "s1",
      started_at: "2026-05-20T10:00:00Z",
      workout_exercises: [
        makeWe({
          id: "we1",
          sets: [
            makeSet({ id: "set1", set_index: 0, weight_kg: "100.00", reps: 5 }),
            makeSet({ id: "set2", set_index: 1, weight_kg: "105.00", reps: 4 }),
          ],
        }),
      ],
    }),
  ];

  it("picks the best e1RM per day", () => {
    const points = bestE1RMByDay(sessions, "bench", "UTC");
    expect(points).toHaveLength(1);
    // 105 * (1 + 4/30) = 119.00; 100 * (1 + 5/30) = 116.666 -> 105x4 wins
    expect(points[0]!.value).toBeCloseTo(119, 2);
    expect(points[0]!.date).toBe("2026-05-20");
  });

  it("sums volume per day across sets", () => {
    const points = volumeByDay(sessions, "bench", "UTC");
    // 100*5 + 105*4 = 500 + 420 = 920
    expect(points).toEqual([{ date: "2026-05-20", value: 920 }]);
  });

  it("ignores other exercises", () => {
    expect(bestE1RMByDay(sessions, "squat", "UTC")).toEqual([]);
  });
});

describe("groupByWeek", () => {
  it("groups sessions into Mondays in the user's tz", () => {
    const monday = makeSession({ id: "m", started_at: "2026-05-18T15:00:00Z" }); // Mon
    const wednesday = makeSession({ id: "w", started_at: "2026-05-20T15:00:00Z" });
    const nextWeek = makeSession({ id: "n", started_at: "2026-05-26T15:00:00Z" });
    const groups = groupByWeek([monday, wednesday, nextWeek], "UTC");
    expect(groups).toHaveLength(2);
    expect(groups[0]!.weekStart).toBe("2026-05-25");
    expect(groups[1]!.weekStart).toBe("2026-05-18");
    expect(groups[1]!.sessions.map((s) => s.id).sort()).toEqual(["m", "w"]);
  });
});

describe("rollupSession", () => {
  it("computes volume, set count, and PR flag", () => {
    const session = makeSession({
      started_at: "2026-05-20T10:00:00Z",
      ended_at: "2026-05-20T10:45:00Z",
      workout_exercises: [
        makeWe({
          id: "we",
          sets: [
            makeSet({ id: "s1", set_index: 0, weight_kg: "100.00", reps: 5, is_pr: true }),
            makeSet({ id: "s2", set_index: 1, weight_kg: "100.00", reps: 5 }),
          ],
        }),
      ],
    });
    const rollup = rollupSession(session);
    expect(rollup.volumeKg).toBe(1000);
    expect(rollup.setCount).toBe(2);
    expect(rollup.exerciseCount).toBe(1);
    expect(rollup.hasPr).toBe(true);
    expect(rollup.durationMin).toBe(45);
  });
});
