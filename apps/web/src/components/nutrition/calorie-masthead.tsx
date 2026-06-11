"use client";

import type { components } from "@/lib/api/types";

type DaySummary = components["schemas"]["DaySummaryResponse"];
type MealPlanTargets = components["schemas"]["MealPlanTargets"];

interface Props {
  totals: DaySummary | undefined;
  targets: MealPlanTargets | undefined;
}

function n(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

/**
 * The day screen's lead element: a serif calorie figure over a 2px ink rule,
 * with a right-aligned Protein / Carbs / Fat group. Replaces the old ring as
 * the visual lead (Direction A).
 */
export function CalorieMasthead({ totals, targets }: Props) {
  const kcal = Math.round(n(totals?.totals.kcal));
  const kcalTarget = Math.round(n(targets?.target_kcal));
  const left = Math.max(0, kcalTarget - kcal);

  const protein = Math.round(n(totals?.totals.protein_g));
  const carbs = Math.round(n(totals?.totals.carbs_g));
  const fat = Math.round(n(totals?.totals.fat_g));

  return (
    <div className="border-text flex flex-wrap items-baseline gap-x-[18px] gap-y-3 border-b-2 pb-3.5">
      <span className="text-text font-serif text-[52px] leading-[0.95] font-medium tracking-[-0.03em] tabular-nums">
        {kcal.toLocaleString()}
      </span>
      <span className="text-text-tertiary text-base">
        of {kcalTarget > 0 ? kcalTarget.toLocaleString() : "—"} kcal
        {kcalTarget > 0 ? ` · ${left.toLocaleString()} left` : ""}
      </span>
      <div className="ml-auto flex gap-[22px]">
        <MacroColumn label="Protein" value={protein} />
        <MacroColumn label="Carbs" value={carbs} />
        <MacroColumn label="Fat" value={fat} />
      </div>
    </div>
  );
}

function MacroColumn({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-text font-serif text-[22px] font-medium tracking-tight tabular-nums">
        {value}
        <span className="text-text-tertiary text-[12px] font-normal">g</span>
      </span>
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
        {label}
      </span>
    </div>
  );
}
