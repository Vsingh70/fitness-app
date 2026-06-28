"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import {
  SET_FIELD_LABEL,
  SET_TYPE_LABEL,
  TRACKING_COLUMNS,
  blockCountsAsVolume,
  isStructuredSetType,
  sumSegmentReps,
  type Exercise,
  type TrackingType,
  type WorkoutExercise,
  type WorkoutSet,
} from "@/lib/workouts/types";

function structuredSummary(set: WorkoutSet): string {
  if (set.set_type === "interval") {
    const work = set.segments.find((s) => s.kind === "work");
    const rest = set.segments.find((s) => s.kind === "rest");
    return `${set.rounds ?? "?"}× ${work?.duration_seconds ?? "?"}s${
      rest ? ` / ${rest.duration_seconds}s rest` : ""
    }`;
  }
  const bouts = set.segments.filter((s) => s.kind === "mini_set");
  return `${bouts.map((b) => b.reps ?? 0).join("+")} = ${sumSegmentReps(bouts)} reps${
    set.weight_kg ? ` @ ${set.weight_kg}kg` : ""
  }`;
}

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
        const nonVolume = !blockCountsAsVolume(we.block_kind);
        return (
          <Card key={we.id}>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-3 tracking-normal normal-case">
                <h3 className="text-text font-serif text-xl font-medium tracking-tight">
                  {meta?.name ?? "Exercise"}
                </h3>
                <span className="border-border-strong text-text-secondary inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                  {tracking}
                </span>
                {nonVolume ? (
                  <span className="border-border text-text-tertiary inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-dashed px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                    {we.block_label?.trim() ||
                      (we.block_kind === "warmup" ? "Warm-up" : "Cooldown")}
                    {" · no volume"}
                  </span>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              <div
                className="text-text-tertiary grid gap-2 px-2 text-[10px] font-semibold tracking-[0.1em] uppercase"
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
                we.sets.map((s, idx) =>
                  isStructuredSetType(s.set_type) || s.set_type === "interval" ? (
                    <div
                      key={s.id}
                      className={cn(
                        "flex items-center gap-2 rounded-[var(--radius-button)] px-2 py-1 text-sm",
                        s.is_pr ? "bg-pr-soft" : "",
                      )}
                    >
                      <span className="text-text-secondary font-serif text-[15px] tabular-nums">
                        {idx + 1}
                      </span>
                      <span className="border-border-strong text-text-secondary inline-flex h-[20px] items-center rounded-[var(--radius-pill)] border px-2 text-[10px] font-semibold tracking-[0.08em] uppercase">
                        {SET_TYPE_LABEL[s.set_type]}
                      </span>
                      <span className="text-text font-serif text-[15px] tabular-nums">
                        {structuredSummary(s)}
                      </span>
                      {s.is_pr ? (
                        <span className="text-pr text-[10px] font-semibold tracking-[0.1em] uppercase">
                          PR
                        </span>
                      ) : null}
                    </div>
                  ) : (
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
                      <span className="text-text-secondary font-serif text-[15px] tabular-nums">
                        {idx + 1}
                      </span>
                      {columns.map((c) => {
                        const value = s[c as keyof WorkoutSet];
                        const display =
                          value === null || value === undefined || typeof value === "object"
                            ? "-"
                            : value;
                        return (
                          <span key={c} className="font-serif text-[15px] tabular-nums">
                            {display}
                          </span>
                        );
                      })}
                      <span
                        className={cn(
                          "text-[10px] font-semibold tracking-[0.1em] uppercase",
                          s.is_pr ? "text-pr" : "text-text-tertiary",
                        )}
                      >
                        {s.is_pr ? "PR" : ""}
                      </span>
                    </div>
                  ),
                )
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
