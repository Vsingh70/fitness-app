"use client";

import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import { useSession } from "@/lib/hooks/workouts";
import type { WorkoutSet } from "@/lib/workouts/types";

function totalVolume(sets: WorkoutSet[]): number {
  return sets.reduce((acc, s) => {
    const w = s.weight_kg ? Number(s.weight_kg) : 0;
    const r = s.reps ?? 0;
    return acc + w * r;
  }, 0);
}

export default function WorkoutSummaryPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const session = useSession(params.id);

  if (session.isLoading) return <p className="text-text-secondary">Loading summary...</p>;
  if (session.isError || !session.data) return <p className="text-destructive">Could not load.</p>;

  const s = session.data;
  const startMs = new Date(s.started_at).getTime();
  const endMs = s.ended_at ? new Date(s.ended_at).getTime() : Date.now();
  const durationMin = Math.max(0, Math.round((endMs - startMs) / 60000));
  const allSets = s.workout_exercises.flatMap((we) => we.sets);
  const setCount = allSets.length;
  const volume = totalVolume(allSets);
  const prCount = allSets.filter((set) => set.is_pr).length;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{s.name ?? "Workout summary"}</h1>
          <p className="text-text-secondary text-sm">Finished {new Date(endMs).toLocaleString()}</p>
        </div>
        <Button type="button" onClick={() => router.push("/")}>
          Done
        </Button>
      </header>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Duration" value={durationMin} unit="min" />
        <StatTile label="Volume" value={Math.round(volume)} unit="kg" />
        <StatTile label="Sets" value={setCount} />
        <StatTile label="PRs" value={prCount} trend={prCount > 0 ? "up" : "flat"} />
      </section>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Exercises</h2>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {s.workout_exercises.length === 0 ? (
            <p className="text-text-secondary">No exercises logged.</p>
          ) : (
            s.workout_exercises.map((we) => (
              <div key={we.id} className="flex items-center justify-between text-sm">
                <span className="font-medium">{we.exercise_id.slice(0, 8)}...</span>
                <span className="text-text-secondary">{we.sets.length} sets</span>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <p className="text-text-tertiary text-xs">
        Per-muscle volume distribution lands in the analytics phase.
      </p>
    </div>
  );
}
