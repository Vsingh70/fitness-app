"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Exercise, WorkoutExercise } from "@/lib/workouts/types";

interface Props {
  workoutExercises: WorkoutExercise[];
  exerciseMeta: Map<string, Exercise>;
}

function workingSetsByMuscle(
  workoutExercises: WorkoutExercise[],
  exerciseMeta: Map<string, Exercise>,
): { muscle: string; sets: number }[] {
  const totals = new Map<string, number>();
  for (const we of workoutExercises) {
    const meta = exerciseMeta.get(we.exercise_id);
    if (!meta) continue;
    const working = we.sets.filter((s) => s.set_type !== "warmup").length;
    if (working === 0) continue;

    const primary = meta.primary_muscle;
    totals.set(primary, (totals.get(primary) ?? 0) + working);

    for (const secondary of meta.secondary_muscles ?? []) {
      totals.set(secondary, (totals.get(secondary) ?? 0) + working * 0.5);
    }
  }
  return [...totals.entries()]
    .map(([muscle, sets]) => ({ muscle, sets: Math.round(sets * 10) / 10 }))
    .sort((a, b) => b.sets - a.sets);
}

export function SessionVolumeByMuscle({ workoutExercises, exerciseMeta }: Props) {
  const rows = workingSetsByMuscle(workoutExercises, exerciseMeta);
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <span>Volume by muscle</span>
        </CardHeader>
        <CardContent>
          <p className="text-text-secondary text-sm">No working sets yet.</p>
        </CardContent>
      </Card>
    );
  }

  const max = Math.max(...rows.map((r) => r.sets), 1);
  return (
    <Card>
      <CardHeader>
        <span>Volume by muscle</span>
        <span className="text-text-tertiary text-[11px] font-normal normal-case tracking-normal">
          Primary 1.0 · secondary 0.5
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {rows.map((row) => (
          <div
            key={row.muscle}
            className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-3 text-sm"
          >
            <span className="text-text-secondary text-xs capitalize">
              {row.muscle.replace(/_/g, " ")}
            </span>
            <div className="bg-surface-sunken h-2 overflow-hidden rounded-full">
              <div
                className="bg-accent h-full rounded-full"
                style={{ width: `${Math.max(6, (row.sets / max) * 100)}%` }}
              />
            </div>
            <span className="text-text font-serif text-right tabular-nums">{row.sets}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
