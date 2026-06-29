"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { labelize } from "@/lib/api/exercises";
import { cn } from "@/lib/cn";
import { formatWeight, kgToDisplay, weightUnitLabel } from "@/lib/utils/format-weight";
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

function structuredSummary(set: WorkoutSet, unit?: "metric" | "imperial"): string {
  if (set.set_type === "interval") {
    const work = set.segments.find((s) => s.kind === "work");
    const rest = set.segments.find((s) => s.kind === "rest");
    return `${set.rounds ?? "?"}× ${work?.duration_seconds ?? "?"}s${
      rest ? ` / ${rest.duration_seconds}s rest` : ""
    }`;
  }
  const bouts = set.segments.filter((s) => s.kind === "mini_set");
  return `${bouts.map((b) => b.reps ?? 0).join("+")} = ${sumSegmentReps(bouts)} reps${
    set.weight_kg ? ` @ ${formatWeight(set.weight_kg, unit)}` : ""
  }`;
}

interface ReadOnlySessionViewProps {
  workoutExercises: WorkoutExercise[];
  exerciseMeta: Map<string, Exercise>;
  /** User's unit system; drives weight display (kg vs lb). */
  unit?: "metric" | "imperial";
}

function summarize(set: WorkoutSet, tracking: TrackingType, unit?: "metric" | "imperial"): string {
  const cols = TRACKING_COLUMNS[tracking];
  const parts: string[] = [];
  for (const c of cols) {
    const value = set[c as keyof WorkoutSet];
    if (value === null || value === undefined) continue;
    if (c === "weight_kg") {
      parts.push(formatWeight(value as string | number, unit));
    } else {
      parts.push(
        `${value}${c === "duration_seconds" ? " s" : c === "distance_meters" ? " m" : ""}`,
      );
    }
  }
  return parts.join(" x ");
}

export function ReadOnlySessionView({
  workoutExercises,
  exerciseMeta,
  unit,
}: ReadOnlySessionViewProps) {
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
                  {labelize(tracking)}
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
                  <span key={c}>
                    {c === "weight_kg" ? weightUnitLabel(unit) : SET_FIELD_LABEL[c]}
                  </span>
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
                        {structuredSummary(s, unit)}
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
                        let display: string | number;
                        if (c === "weight_kg") {
                          display = kgToDisplay(value as string | null, unit) ?? "-";
                        } else if (
                          value === null ||
                          value === undefined ||
                          typeof value === "object"
                        ) {
                          display = "-";
                        } else {
                          display = value as string | number;
                        }
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
                Summary: {we.sets.map((s) => summarize(s, tracking, unit)).join(" · ") || "no sets"}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
