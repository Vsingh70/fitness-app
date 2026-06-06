"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { Exercise, WorkoutExercise } from "@/lib/workouts/types";

interface Props {
  workoutExercises: WorkoutExercise[];
  exerciseMeta: Map<string, Exercise>;
}

const SET_TYPE_LABEL: Record<string, string> = {
  working: "",
  warmup: "warmup",
  drop: "drop",
  myo_rep: "myo-rep",
  cluster: "cluster",
  top_set: "top set",
  back_off: "back off",
  amrap: "amrap",
};

function dec(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? `${n}` : "—";
}

export function SetByExerciseTable({ workoutExercises, exerciseMeta }: Props) {
  const totalSets = workoutExercises.reduce((acc, we) => acc + we.sets.length, 0);

  if (workoutExercises.length === 0 || totalSets === 0) {
    return (
      <Card>
        <CardHeader>
          <span>Set by set</span>
        </CardHeader>
        <CardContent>
          <p className="text-text-secondary text-sm">No sets logged.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <span>Set by set</span>
        <span className="text-text-tertiary text-[11px] font-normal tracking-normal normal-case">
          {workoutExercises.length} exercises · {totalSets} sets
        </span>
      </CardHeader>
      <CardContent className="px-0 pt-0">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="border-border-strong text-text-tertiary border-b text-[10px] font-semibold tracking-[0.1em] uppercase">
              <th className="px-4 py-3 text-left">Exercise</th>
              <th className="px-2 py-3 text-left">Set</th>
              <th className="px-2 py-3 text-right">Weight</th>
              <th className="px-2 py-3 text-right">Reps</th>
              <th className="px-2 py-3 pr-4 text-right">RPE</th>
            </tr>
          </thead>
          <tbody>
            {workoutExercises.flatMap((we) => {
              const meta = exerciseMeta.get(we.exercise_id);
              const name = meta?.name ?? "Exercise";
              return we.sets.map((set, idx) => {
                const isPr = set.is_pr;
                const isWarmup = set.set_type === "warmup";
                const setLabel = isWarmup
                  ? `w${idx + 1}`
                  : SET_TYPE_LABEL[set.set_type]
                    ? `${idx + 1} (${SET_TYPE_LABEL[set.set_type]})`
                    : `${idx + 1}`;
                return (
                  <tr
                    key={set.id}
                    className={cn(
                      "border-border border-b last:border-b-0",
                      isPr ? "bg-pr-soft" : "",
                      isWarmup ? "text-text-tertiary" : "",
                    )}
                  >
                    <td className={cn("px-4 py-3", isPr ? "border-pr border-l-[3px] pl-3" : "")}>
                      {idx === 0 ? <span className="text-text font-medium">{name}</span> : null}
                    </td>
                    <td className="text-text-secondary px-2 py-3 font-serif">{setLabel}</td>
                    <td className="px-2 py-3 text-right font-serif">{dec(set.weight_kg)}</td>
                    <td className="px-2 py-3 text-right font-serif">{dec(set.reps)}</td>
                    <td className="px-2 py-3 pr-4 text-right font-serif">{dec(set.rpe)}</td>
                  </tr>
                );
              });
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
