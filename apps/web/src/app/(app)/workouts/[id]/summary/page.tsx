"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import { NextSessionRecs } from "@/components/workouts/summary/next-session-recs";
import { PrBanner } from "@/components/workouts/summary/pr-banner";
import { SessionVolumeByMuscle } from "@/components/workouts/summary/session-volume-by-muscle";
import { SetByExerciseTable } from "@/components/workouts/summary/set-by-exercise-table";
import { searchExercises } from "@/lib/api/workouts";
import { useRecommendations } from "@/lib/hooks/today";
import { useSession } from "@/lib/hooks/workouts";
import type { Exercise, WorkoutSet } from "@/lib/workouts/types";

function brzyckiE1RM(weight: number, reps: number): number | null {
  if (weight <= 0 || reps <= 0 || reps >= 37) return null;
  return weight * (36 / (37 - reps));
}

function decimalSetWeight(set: WorkoutSet): number | null {
  if (set.weight_kg == null) return null;
  const n = typeof set.weight_kg === "number" ? set.weight_kg : Number(set.weight_kg);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function totalVolume(sets: WorkoutSet[]): number {
  return sets.reduce((acc, s) => {
    const w = decimalSetWeight(s) ?? 0;
    const r = s.reps ?? 0;
    return acc + w * r;
  }, 0);
}

function meanRpe(sets: WorkoutSet[]): number | null {
  const values: number[] = [];
  for (const s of sets) {
    if (s.set_type === "warmup") continue;
    if (s.rpe == null) continue;
    const n = typeof s.rpe === "number" ? s.rpe : Number(s.rpe);
    if (Number.isFinite(n)) values.push(n);
  }
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export default function WorkoutSummaryPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const session = useSession(params.id);
  const recommendations = useRecommendations();

  const exerciseIds = useMemo(
    () => (session.data ? session.data.workout_exercises.map((we) => we.exercise_id) : []),
    [session.data],
  );

  const exercisesQuery = useQuery({
    queryKey: ["exercise-meta", [...exerciseIds].sort().join(",")],
    queryFn: async () => {
      if (exerciseIds.length === 0) return new Map<string, Exercise>();
      const list = await searchExercises(undefined, { limit: 200 });
      const map = new Map<string, Exercise>();
      for (const ex of list.items) if (exerciseIds.includes(ex.id)) map.set(ex.id, ex);
      return map;
    },
    enabled: exerciseIds.length > 0,
    staleTime: 60_000,
  });

  if (session.isLoading) return <p className="text-text-secondary">Loading summary…</p>;
  if (session.isError || !session.data) return <p className="text-destructive">Could not load.</p>;

  const s = session.data;
  const startMs = new Date(s.started_at).getTime();
  const endMs = s.ended_at ? new Date(s.ended_at).getTime() : Date.now();
  const durationMin = Math.max(0, Math.round((endMs - startMs) / 60000));
  const allSets = s.workout_exercises.flatMap((we) => we.sets);
  const workingSets = allSets.filter((set) => set.set_type !== "warmup");
  const setCount = workingSets.length;
  const volume = totalVolume(workingSets);
  const avgRpe = meanRpe(allSets);
  const exerciseMeta = exercisesQuery.data ?? new Map<string, Exercise>();

  // PR list — one entry per exercise that had a PR, picking the best set.
  const prs = s.workout_exercises
    .map((we) => {
      const prSets = we.sets.filter((set) => set.is_pr);
      if (prSets.length === 0) return null;
      const best = prSets.reduce<WorkoutSet | null>((acc, set) => {
        const w = decimalSetWeight(set);
        const wAcc = acc ? decimalSetWeight(acc) : null;
        if (w !== null && (wAcc === null || w > wAcc)) return set;
        return acc;
      }, null);
      if (!best) return null;
      const weightKg = decimalSetWeight(best);
      const reps = best.reps;
      const e1rm = weightKg !== null && reps !== null ? brzyckiE1RM(weightKg, reps) : null;
      return {
        exerciseId: we.exercise_id,
        exerciseName: exerciseMeta.get(we.exercise_id)?.name ?? "Exercise",
        weightKg,
        reps,
        estimated1Rm: e1rm,
      };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null);

  const sessionExerciseIds = new Set(s.workout_exercises.map((we) => we.exercise_id));
  const nextSessionRecs =
    recommendations.data?.items.filter(
      (rec) =>
        sessionExerciseIds.has(rec.exercise_id) &&
        rec.consumed_at === null &&
        rec.dismissed_at === null,
    ) ?? [];

  const finishedAt = new Date(endMs);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 pb-10">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
            {s.ended_at ? "Finished" : "In progress"}
          </span>
          <h1 className="mt-1 font-serif text-[28px] font-medium tracking-tight md:text-[32px]">
            {s.name ?? "Workout summary"}
          </h1>
          <p className="text-text-secondary text-sm">
            {finishedAt.toLocaleString(undefined, {
              weekday: "long",
              month: "long",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            })}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => router.push(`/workouts/${s.id}`)}>
            Edit session
          </Button>
          <Button size="sm" onClick={() => router.push("/")}>
            Done
          </Button>
        </div>
      </header>

      <PrBanner prs={prs} />

      <section className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <StatTile label="Duration" value={durationMin} unit="min" />
        <StatTile label="Working sets" value={setCount} />
        <StatTile label="Volume" value={Math.round(volume).toLocaleString()} unit="kg" />
        <StatTile label="Avg RPE" value={avgRpe !== null ? avgRpe.toFixed(1) : "—"} />
      </section>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <SetByExerciseTable workoutExercises={s.workout_exercises} exerciseMeta={exerciseMeta} />
        <div className="flex flex-col gap-4">
          <SessionVolumeByMuscle
            workoutExercises={s.workout_exercises}
            exerciseMeta={exerciseMeta}
          />
          <NextSessionRecs recommendations={nextSessionRecs} exerciseMeta={exerciseMeta} />
          {s.notes ? (
            <Card>
              <CardHeader>
                <span>Session notes</span>
              </CardHeader>
              <CardContent>
                <p className="text-text-secondary text-sm leading-relaxed">{s.notes}</p>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap justify-end gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/workouts")}>
          Back to workouts
        </Button>
      </div>
    </div>
  );
}
