"use client";

import type { components } from "@/lib/api/types";

type Predicted = components["schemas"]["PredictedNextSessionResponse"];

interface Props {
  predicted: Predicted;
}

const KIND_LABEL: Record<NonNullable<Predicted["kind"]>, string> = {
  increase_weight: "Add weight",
  increase_reps: "Add reps",
  hold: "Hold steady",
  deload: "Deload",
  swap: "Swap variant",
  add_set: "Add a set",
  remove_set: "Cut a set",
};

function summarize(p: Predicted): string {
  const weight = p.suggested_weight_kg ? `${Number(p.suggested_weight_kg)} kg` : null;
  const reps =
    p.suggested_reps_low !== null && p.suggested_reps_high !== null
      ? `${p.suggested_reps_low}–${p.suggested_reps_high} reps`
      : null;
  if (!p.kind) return "Predicted next session";
  switch (p.kind) {
    case "increase_weight":
      return weight ? `Try ${weight}` : "Add weight";
    case "increase_reps":
      return reps ? `Push to ${reps}` : "Add reps";
    case "hold":
      return weight ? `Hold ${weight}` : "Hold steady";
    case "deload":
      return "Deload this session";
    case "swap":
      return "Consider a variant";
    case "add_set":
      return "Add a working set";
    case "remove_set":
      return "Cut a set";
  }
}

export function PredictedNextStrip({ predicted }: Props) {
  if (!predicted.has_prediction || !predicted.kind) return null;
  const headline = summarize(predicted);
  return (
    <div className="bg-accent-soft grid grid-cols-[1fr_auto] items-center gap-4 rounded-[var(--radius-card)] px-4 py-3.5">
      <div className="min-w-0">
        <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
          {KIND_LABEL[predicted.kind]}
          {predicted.is_deload ? " · Deload" : ""}
        </span>
        <div className="text-text text-sm font-semibold">{headline}</div>
        {predicted.rationale ? (
          <div className="text-text-secondary mt-0.5 text-[12px] leading-snug">
            {predicted.rationale}
          </div>
        ) : null}
      </div>
      <span className="text-text-tertiary font-mono text-[10px] tracking-[0.08em] uppercase">
        {predicted.source}
      </span>
    </div>
  );
}
