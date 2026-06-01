"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import {
  SET_FIELD_LABEL,
  TRACKING_COLUMNS,
  type Exercise,
  type TrackingType,
  type WorkoutExercise,
  type WorkoutSet,
} from "@/lib/workouts/types";

interface ReadOnlySessionViewProps {
  workoutExercises: WorkoutExercise[];
  exerciseMeta: Map<string, Exercise>;
}

function summarize(set: WorkoutSet, tracking: TrackingType): string {
  const cols = TRACKING_COLUMNS[tracking];
  const parts: string[] = [];
  for (const c of cols) {
    const value = set[c as keyof WorkoutSet];
    if (value === null || value === undefined) continue;
    parts.push(
      `${value}${c === "weight_kg" ? " kg" : c === "duration_seconds" ? " s" : c === "distance_meters" ? " m" : ""}`,
    );
  }
  return parts.join(" x ");
}

export function ReadOnlySessionView({ workoutExercises, exerciseMeta }: ReadOnlySessionViewProps) {
  if (workoutExercises.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-text-secondary">No exercises logged.</p>
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {workoutExercises.map((we) => {
        const meta = exerciseMeta.get(we.exercise_id);
        const tracking = (meta?.tracking_type ?? "weight_reps") as TrackingType;
        const columns = TRACKING_COLUMNS[tracking];
        return (
          <Card key={we.id}>
            <CardHeader>
              <div className="flex items-center gap-3 normal-case tracking-normal">
                <h3 className="font-serif text-text text-xl font-medium tracking-tight">
                  {meta?.name ?? "Exercise"}
                </h3>
                <span className="border-border-strong text-text-secondary inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold uppercase tracking-[0.1em]">
                  {tracking}
                </span>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              <div
                className="text-text-tertiary grid gap-2 px-2 text-[10px] font-semibold uppercase tracking-[0.1em]"
                style={{
                  gridTemplateColumns: `2rem repeat(${columns.length}, minmax(0, 1fr)) auto`,
                }}
              >
                <span>Set</span>
                {columns.map((c) => (
                  <span key={c}>{SET_FIELD_LABEL[c]}</span>
                ))}
                <span></span>
              </div>
              {we.sets.length === 0 ? (
                <p className="text-text-tertiary px-2 text-xs">No sets recorded.</p>
              ) : (
                we.sets.map((s, idx) => (
                  <div
                    key={s.id}
                    className={cn(
                      "grid items-center gap-2 rounded-[var(--radius-button)] px-2 py-1 text-sm",
                      s.is_pr ? "bg-pr-soft" : "",
                    )}
                    style={{
                      gridTemplateColumns: `2rem repeat(${columns.length}, minmax(0, 1fr)) auto`,
                    }}
                  >
                    <span className="text-text-secondary font-serif tabular-nums text-[15px]">
                      {idx + 1}
                    </span>
                    {columns.map((c) => (
                      <span key={c} className="font-serif tabular-nums text-[15px]">
                        {s[c as keyof WorkoutSet] ?? "-"}
                      </span>
                    ))}
                    <span
                      className={cn(
                        "text-[10px] font-semibold uppercase tracking-[0.1em]",
                        s.is_pr ? "text-pr" : "text-text-tertiary",
                      )}
                    >
                      {s.is_pr ? "PR" : ""}
                    </span>
                  </div>
                ))
              )}
              <p className="text-text-tertiary px-2 text-xs">
                Summary: {we.sets.map((s) => summarize(s, tracking)).join(" · ") || "no sets"}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
