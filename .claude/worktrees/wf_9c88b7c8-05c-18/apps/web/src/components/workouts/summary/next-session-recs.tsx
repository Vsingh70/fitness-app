"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { components } from "@/lib/api/types";
import type { Exercise } from "@/lib/workouts/types";

type Recommendation = components["schemas"]["RecommendationResponse"];

interface Props {
  recommendations: Recommendation[];
  exerciseMeta: Map<string, Exercise>;
}

const KIND_LABEL: Record<Recommendation["kind"], string> = {
  increase_weight: "Add weight",
  increase_reps: "Add reps",
  hold: "Hold",
  deload: "Deload",
  swap: "Swap",
  add_set: "Add set",
  remove_set: "Cut set",
};

function summarize(rec: Recommendation, name: string): string {
  const weight = rec.suggested_weight_kg ? `${Number(rec.suggested_weight_kg)} kg` : null;
  const reps =
    rec.suggested_reps_low !== null && rec.suggested_reps_high !== null
      ? `${rec.suggested_reps_low}–${rec.suggested_reps_high} reps`
      : null;
  switch (rec.kind) {
    case "increase_weight":
      return weight ? `${name}: try ${weight}` : `${name}: more weight`;
    case "increase_reps":
      return reps ? `${name}: push to ${reps}` : `${name}: more reps`;
    case "hold":
      return `${name}: hold this load`;
    case "deload":
      return `${name}: deload this week`;
    case "swap":
      return `${name}: swap variant`;
    case "add_set":
      return `${name}: +1 set`;
    case "remove_set":
      return `${name}: -1 set`;
  }
}

export function NextSessionRecs({ recommendations, exerciseMeta }: Props) {
  if (recommendations.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <span>Next session</span>
        <span className="text-text-tertiary text-[11px] font-normal normal-case tracking-normal">
          {recommendations.length} recommendation{recommendations.length === 1 ? "" : "s"}
        </span>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2">
        {recommendations.slice(0, 4).map((rec) => {
          const name = exerciseMeta.get(rec.exercise_id)?.name ?? "Exercise";
          return (
            <div
              key={rec.id}
              className="border-border bg-surface flex flex-col gap-1 rounded-[var(--radius-card)] border p-3"
            >
              <span className="text-text-tertiary text-[10px] font-semibold uppercase tracking-[0.08em]">
                {KIND_LABEL[rec.kind]}
              </span>
              <span className="text-text text-sm font-semibold">
                {summarize(rec, name)}
              </span>
              {rec.rationale ? (
                <span className="text-text-secondary text-[12px] leading-snug">
                  {rec.rationale}
                </span>
              ) : null}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
