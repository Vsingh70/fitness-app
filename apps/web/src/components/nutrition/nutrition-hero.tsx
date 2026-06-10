"use client";

import type { TrackingMode } from "@/lib/api/meal-plans";
import type { components } from "@/lib/api/types";
import { showsKcal, showsMacros } from "@/lib/nutrition/macros";

type DaySummary = components["schemas"]["DaySummaryResponse"];
type MealPlanTargets = components["schemas"]["MealPlanTargets"];
type DayAdherence = components["schemas"]["DayAdherence"];

interface Props {
  totals: DaySummary | undefined;
  targets: MealPlanTargets | undefined;
  /** The active plan's tracking mode; drives which figures are shown. */
  trackingMode?: TrackingMode | null;
  adherence?: DayAdherence | null;
}

const R = 74;
const CIRC = 2 * Math.PI * R;

function n(value: string | undefined | null): number {
  if (value == null) return 0;
  const x = Number(value);
  return Number.isFinite(x) ? x : 0;
}

function pct(consumed: number, target: number): string {
  if (target <= 0) return "0%";
  return `${Math.min(100, (consumed / target) * 100).toFixed(0)}%`;
}

function barWidth(consumed: number, target: number): string {
  if (target <= 0) return "0%";
  return `${Math.min(100, (consumed / target) * 100).toFixed(1)}%`;
}

export function NutritionHero({ totals, targets, trackingMode, adherence }: Props) {
  const mode: TrackingMode = trackingMode ?? "macros_and_calories";
  const withKcal = showsKcal(mode);
  const withMacros = showsMacros(mode);

  const kcal = Math.round(n(totals?.totals.kcal));
  const kcalTarget = Math.round(n(targets?.target_kcal));
  const remaining = Math.max(0, kcalTarget - kcal);
  const kcalFraction = kcalTarget > 0 ? Math.min(1, kcal / kcalTarget) : 0;
  const dash = CIRC * (1 - kcalFraction);

  const protein = Math.round(n(totals?.totals.protein_g));
  const carbs = Math.round(n(totals?.totals.carbs_g));
  const fat = Math.round(n(totals?.totals.fat_g));
  const fiber = Math.round(n(totals?.totals.fiber_g));

  const proteinTarget = Math.round(n(targets?.target_protein_g));
  const carbsTarget = Math.round(n(targets?.target_carbs_g));
  const fatTarget = Math.round(n(targets?.target_fat_g));

  return (
    <div
      className={`border-border bg-surface-elevated grid items-center gap-8 rounded-[var(--radius-card)] border px-6 py-6 ${
        withKcal && withMacros ? "md:grid-cols-[auto_1fr]" : ""
      }`}
      style={{
        backgroundImage:
          "radial-gradient(700px 280px at 100% 0%, var(--color-accent-soft), transparent 60%)",
      }}
    >
      {withKcal ? (
        <div className="relative mx-auto h-[180px] w-[180px] shrink-0">
          <svg width="180" height="180" viewBox="0 0 180 180" className="-rotate-90">
            <circle cx="90" cy="90" r={R} fill="none" stroke="var(--color-border)" strokeWidth="14" />
            {kcalTarget > 0 ? (
              <circle
                cx="90"
                cy="90"
                r={R}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth="14"
                strokeLinecap="round"
                strokeDasharray={CIRC}
                strokeDashoffset={dash}
              />
            ) : null}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-text font-serif text-[36px] leading-none font-medium tracking-tight tabular-nums">
              {kcal.toLocaleString()}
            </span>
            <span className="text-text-tertiary mt-1.5 text-[12px]">
              of {kcalTarget > 0 ? kcalTarget.toLocaleString() : "—"} kcal
            </span>
          </div>
        </div>
      ) : null}

      {withMacros ? (
        <div>
          <div className="grid gap-4 sm:grid-cols-4">
            <MacroCell
              label="Protein"
              value={protein}
              target={proteinTarget}
              unit="g"
              fill="bg-accent"
            />
            <MacroCell label="Carbs" value={carbs} target={carbsTarget} unit="g" fill="bg-warning" />
            <MacroCell label="Fat" value={fat} target={fatTarget} unit="g" fill="bg-success" />
            <MacroCell label="Fiber" value={fiber} target={0} unit="g" fill="bg-text-tertiary" />
          </div>
          <div className="text-text-tertiary mt-5 flex flex-wrap gap-5 text-[12px]">
            {withKcal && kcalTarget > 0 ? (
              <span>
                <b className="text-text-secondary font-serif font-medium tabular-nums">
                  {remaining.toLocaleString()}
                </b>{" "}
                kcal remaining
              </span>
            ) : null}
            {proteinTarget > 0 ? (
              <span>
                <b className="text-text-secondary font-serif font-medium tabular-nums">
                  {pct(protein, proteinTarget)}
                </b>{" "}
                of protein goal
              </span>
            ) : null}
            {adherence && adherence.planned_meals > 0 ? (
              <span>
                <b className="text-text-secondary font-serif font-medium tabular-nums">
                  {adherence.completed_meals} of {adherence.planned_meals}
                </b>{" "}
                meals complete
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Calories-only: surface remaining + adherence without the macro grid. */}
      {withKcal && !withMacros ? (
        <div className="text-text-tertiary mt-2 flex flex-wrap gap-5 text-[12px]">
          {kcalTarget > 0 ? (
            <span>
              <b className="text-text-secondary font-serif font-medium tabular-nums">
                {remaining.toLocaleString()}
              </b>{" "}
              kcal remaining
            </span>
          ) : null}
          {adherence && adherence.planned_meals > 0 ? (
            <span>
              <b className="text-text-secondary font-serif font-medium tabular-nums">
                {adherence.completed_meals} of {adherence.planned_meals}
              </b>{" "}
              meals complete
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function MacroCell({
  label,
  value,
  target,
  unit,
  fill,
}: {
  label: string;
  value: number;
  target: number;
  unit: string;
  fill: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span className="text-text font-serif text-[22px] font-medium tracking-tight tabular-nums">
          {value}
        </span>
        <span className="text-text-secondary text-[11px] font-medium">{unit}</span>
      </div>
      <div className="bg-surface relative h-[5px] overflow-hidden rounded-full">
        <div className={`h-full rounded-full ${fill}`} style={{ width: barWidth(value, target) }} />
      </div>
      <span className="text-text-tertiary text-[11px]">
        {target > 0 ? `of ${target} ${unit}` : "no target"}
      </span>
    </div>
  );
}
