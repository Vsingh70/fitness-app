"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { components } from "@/lib/api/types";

type Recommendation = components["schemas"]["RecommendationResponse"];
type Kind = Recommendation["kind"];

interface Props {
  rec: Recommendation;
  exerciseName?: string;
}

const KIND_LABEL: Record<Kind, string> = {
  increase_weight: "Add weight",
  increase_reps: "Add reps",
  hold: "Hold steady",
  deload: "Deload",
  swap: "Swap exercise",
  add_set: "Add set",
  remove_set: "Remove set",
};

function title(rec: Recommendation, exerciseName: string): string {
  const weight = rec.suggested_weight_kg ? `${Number(rec.suggested_weight_kg)} kg` : null;
  const reps =
    rec.suggested_reps_low !== null && rec.suggested_reps_high !== null
      ? `${rec.suggested_reps_low}–${rec.suggested_reps_high} reps`
      : null;
  switch (rec.kind) {
    case "increase_weight":
      return weight ? `Try ${weight} on ${exerciseName}` : `Add weight to ${exerciseName}`;
    case "increase_reps":
      return reps ? `Push to ${reps} on ${exerciseName}` : `Add reps on ${exerciseName}`;
    case "hold":
      return `Hold ${exerciseName} steady`;
    case "deload":
      return `Deload ${exerciseName} this week`;
    case "swap":
      return `Swap ${exerciseName}`;
    case "add_set":
      return `Add a set on ${exerciseName}`;
    case "remove_set":
      return `Cut a set on ${exerciseName}`;
  }
}

function confidenceFromPayload(payload: Recommendation["payload"]): "low" | "medium" | "high" {
  const raw = payload?.confidence;
  if (raw === "low" || raw === "medium" || raw === "high") return raw;
  return "medium";
}

const CONF_PIPS: Record<"low" | "medium" | "high", number> = { low: 1, medium: 2, high: 3 };

export function RecommendationCard({ rec, exerciseName = "this lift" }: Props) {
  const conf = confidenceFromPayload(rec.payload);
  const lit = CONF_PIPS[conf];

  return (
    <Card>
      <CardContent className="flex h-full flex-col gap-2">
        <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
          {KIND_LABEL[rec.kind]}
        </span>
        <h3 className="text-text font-serif text-[18px] leading-tight font-medium tracking-tight">
          {title(rec, exerciseName)}
        </h3>
        {rec.rationale ? (
          <p className="text-text-secondary text-[13px] leading-relaxed">{rec.rationale}</p>
        ) : null}
        <div className="border-border mt-auto flex items-center justify-between border-t pt-3">
          <span className="flex items-center gap-[3px]" aria-label={`Confidence: ${conf}`}>
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  i < lit ? "bg-accent" : "bg-border-strong",
                )}
              />
            ))}
          </span>
          <button
            type="button"
            className="text-text-secondary hover:text-text text-[11px] font-semibold tracking-[0.08em] uppercase"
          >
            {conf === "high" ? "Apply to today" : "Why?"}
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
