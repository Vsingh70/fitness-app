/**
 * Pure helpers for history aggregation and grouping. Tested in
 * tests/history.test.ts.
 */

import type { WorkoutSession, WorkoutSet } from "@/lib/workouts/types";

export type RangeKey = "4w" | "12w" | "6mo" | "1y" | "all";

const DAY_MS = 24 * 60 * 60 * 1000;
const RANGE_DAYS: Record<RangeKey, number | null> = {
  "4w": 28,
  "12w": 84,
  "6mo": 182,
  "1y": 365,
  all: null,
};

export function rangeStartMs(range: RangeKey, now = Date.now()): number | null {
  const days = RANGE_DAYS[range];
  return days === null ? null : now - days * DAY_MS;
}

/** Filters sessions to those whose started_at falls within [start, now]. */
export function filterSessionsByRange(
  sessions: WorkoutSession[],
  range: RangeKey,
  now = Date.now(),
): WorkoutSession[] {
  const start = rangeStartMs(range, now);
  if (start === null) return sessions;
  return sessions.filter((s) => new Date(s.started_at).getTime() >= start);
}

/** Epley estimated one-rep max. Returns 0 when reps <= 0 or weight missing. */
export function epleyE1RM(weightKg: number, reps: number): number {
  if (reps <= 0 || weightKg <= 0) return 0;
  return weightKg * (1 + reps / 30);
}

/** Best e1RM per session date for one exercise, in chronological order. */
export interface E1RMPoint {
  date: string; // YYYY-MM-DD in the user's timezone
  value: number;
}

export function bestE1RMByDay(
  sessions: WorkoutSession[],
  exerciseId: string,
  timezone: string,
): E1RMPoint[] {
  const byDay = new Map<string, number>();
  for (const session of sessions) {
    const day = isoDayInTz(session.started_at, timezone);
    for (const we of session.workout_exercises) {
      if (we.exercise_id !== exerciseId) continue;
      for (const s of we.sets) {
        const w = s.weight_kg != null ? Number(s.weight_kg) : 0;
        const r = s.reps ?? 0;
        const e1rm = epleyE1RM(w, r);
        if (e1rm === 0) continue;
        const current = byDay.get(day) ?? 0;
        if (e1rm > current) byDay.set(day, e1rm);
      }
    }
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, value]) => ({ date, value: Math.round(value * 100) / 100 }));
}

/** Total volume (sum of weight*reps) per session date for one exercise. */
export function volumeByDay(
  sessions: WorkoutSession[],
  exerciseId: string,
  timezone: string,
): E1RMPoint[] {
  const byDay = new Map<string, number>();
  for (const session of sessions) {
    const day = isoDayInTz(session.started_at, timezone);
    for (const we of session.workout_exercises) {
      if (we.exercise_id !== exerciseId) continue;
      let day_total = 0;
      for (const s of we.sets) {
        const w = s.weight_kg != null ? Number(s.weight_kg) : 0;
        const r = s.reps ?? 0;
        day_total += w * r;
      }
      byDay.set(day, (byDay.get(day) ?? 0) + day_total);
    }
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, value]) => ({ date, value: Math.round(value) }));
}

/** All sets for one exercise across all sessions, flattened. */
export interface SetWithContext {
  setId: string;
  sessionId: string;
  sessionDate: string;
  set: WorkoutSet;
}

export function allSetsForExercise(
  sessions: WorkoutSession[],
  exerciseId: string,
  timezone: string,
): SetWithContext[] {
  const out: SetWithContext[] = [];
  for (const session of sessions) {
    const day = isoDayInTz(session.started_at, timezone);
    for (const we of session.workout_exercises) {
      if (we.exercise_id !== exerciseId) continue;
      for (const s of we.sets) {
        out.push({ setId: s.id, sessionId: session.id, sessionDate: day, set: s });
      }
    }
  }
  return out.sort((a, b) => b.sessionDate.localeCompare(a.sessionDate));
}

/** YYYY-MM-DD for an ISO timestamp, computed in the given IANA timezone. */
export function isoDayInTz(iso: string, timezone: string): string {
  const date = new Date(iso);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
  // en-CA returns YYYY-MM-DD natively.
  return parts;
}

export interface WeekGroup {
  weekStart: string; // YYYY-MM-DD of Monday in the user's tz
  weekLabel: string; // "Week of Mar 3"
  sessions: WorkoutSession[];
}

/** Groups sessions into weeks starting Monday in the user's timezone. */
export function groupByWeek(sessions: WorkoutSession[], timezone: string): WeekGroup[] {
  const map = new Map<string, WorkoutSession[]>();
  for (const session of sessions) {
    const day = isoDayInTz(session.started_at, timezone);
    const monday = mondayOf(day);
    if (!map.has(monday)) map.set(monday, []);
    map.get(monday)!.push(session);
  }
  return [...map.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([weekStart, sessions]) => ({
      weekStart,
      weekLabel: prettyWeek(weekStart),
      sessions: sessions.sort(
        (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
      ),
    }));
}

function mondayOf(yyyyMmDd: string): string {
  const [y, m, d] = yyyyMmDd.split("-").map((s) => Number.parseInt(s, 10));
  // Treat as UTC noon to avoid DST edge cases; we only care about the weekday.
  const date = new Date(Date.UTC(y!, m! - 1, d!, 12));
  const dow = date.getUTCDay(); // 0..6, Sun..Sat
  const diff = (dow + 6) % 7; // days back to Monday
  date.setUTCDate(date.getUTCDate() - diff);
  return date.toISOString().slice(0, 10);
}

function prettyWeek(weekStart: string): string {
  const [y, m, d] = weekStart.split("-").map((s) => Number.parseInt(s, 10));
  const date = new Date(Date.UTC(y!, m! - 1, d!, 12));
  return `Week of ${date.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" })}`;
}

/** Volume + duration + set count + PR flag for a single session. */
export interface SessionRollup {
  durationMin: number;
  volumeKg: number;
  setCount: number;
  exerciseCount: number;
  hasPr: boolean;
}

export function rollupSession(session: WorkoutSession): SessionRollup {
  const startMs = new Date(session.started_at).getTime();
  const endMs = session.ended_at ? new Date(session.ended_at).getTime() : Date.now();
  let volumeKg = 0;
  let setCount = 0;
  let hasPr = false;
  for (const we of session.workout_exercises) {
    for (const s of we.sets) {
      setCount += 1;
      if (s.is_pr) hasPr = true;
      const w = s.weight_kg != null ? Number(s.weight_kg) : 0;
      const r = s.reps ?? 0;
      volumeKg += w * r;
    }
  }
  return {
    durationMin: Math.max(0, Math.round((endMs - startMs) / 60000)),
    volumeKg: Math.round(volumeKg),
    setCount,
    exerciseCount: session.workout_exercises.length,
    hasPr,
  };
}
