"use client";

import Link from "next/link";

import type { components } from "@/lib/api/types";

type DaySummary = components["schemas"]["DaySummaryResponse"];
type MealPlanTargets = components["schemas"]["MealPlanTargets"];

interface Props {
  totals: DaySummary | undefined;
  targets: MealPlanTargets | undefined;
}

const R = 40;
const CIRC = 2 * Math.PI * R;

function n(value: string | undefined | null): number {
  if (value == null) return 0;
  const x = Number(value);
  return Number.isFinite(x) ? x : 0;
}

function fractionWidth(consumed: number, target: number): string {
  if (target <= 0) return "0%";
  return `${Math.min(100, (consumed / target) * 100).toFixed(1)}%`;
}

export function NutritionStrip({ totals, targets }: Props) {
  const kcalConsumed = Math.round(n(totals?.totals.kcal));
  const kcalTarget = Math.round(n(targets?.target_kcal)) || 0;
  const kcalRemaining = Math.max(0, kcalTarget - kcalConsumed);
  const kcalFraction =
    kcalTarget > 0 ? Math.max(0, Math.min(1, kcalConsumed / kcalTarget)) : 0;
  const dash = CIRC * (1 - kcalFraction);

  const protein = Math.round(n(totals?.totals.protein_g));
  const carbs = Math.round(n(totals?.totals.carbs_g));
  const fat = Math.round(n(totals?.totals.fat_g));
  const fiber = Math.round(n(totals?.totals.fiber_g));

  const proteinTarget = Math.round(n(targets?.target_protein_g));
  const carbsTarget = Math.round(n(targets?.target_carbs_g));
  const fatTarget = Math.round(n(targets?.target_fat_g));

  return (
    <div className="border-border bg-surface-elevated grid items-center gap-6 rounded-[var(--radius-card)] border p-5 md:grid-cols-[auto_1fr_auto]">
      <div className="relative h-[96px] w-[96px] shrink-0">
        <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
          <circle cx="48" cy="48" r={R} fill="none" stroke="var(--color-border)" strokeWidth="7" />
          {kcalTarget > 0 ? (
            <circle
              cx="48"
              cy="48"
              r={R}
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={CIRC}
              strokeDashoffset={dash}
            />
          ) : null}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-serif text-text text-[22px] font-medium tabular-nums leading-none">
            {kcalConsumed.toLocaleString()}
          </span>
          <span className="text-text-tertiary mt-1 text-[10px]">
            of {kcalTarget.toLocaleString() || "—"} kcal
          </span>
        </div>
      </div>

      <div className="min-w-0">
        <span className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.08em]">
          Nutrition · today
        </span>
        <div className="font-serif mt-1 text-[22px] font-medium tracking-tight">
          {kcalTarget > 0
            ? `${kcalRemaining.toLocaleString()} kcal remaining`
            : "Set a kcal target in Settings"}
        </div>
        <div className="mt-3 flex flex-wrap gap-5">
          <MacroCell label="Protein" value={protein} unit="g" target={proteinTarget} fill="bg-accent" />
          <MacroCell label="Carbs" value={carbs} unit="g" target={carbsTarget} fill="bg-warning" />
          <MacroCell label="Fat" value={fat} unit="g" target={fatTarget} fill="bg-success" />
          <MacroCell label="Fiber" value={fiber} unit="g" target={0} fill="bg-text-tertiary" />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Link
          href="/nutrition"
          className="bg-accent text-accent-foreground inline-flex h-[42px] items-center justify-center gap-2 rounded-[var(--radius-button)] px-[18px] text-sm font-semibold tracking-[0.01em] hover:brightness-105"
        >
          Log a meal
        </Link>
        <Link
          href="/nutrition"
          className="text-text-secondary hover:text-text inline-flex h-9 items-center justify-center text-[13px] font-medium"
        >
          Full day →
        </Link>
      </div>
    </div>
  );
}

function MacroCell({
  label,
  value,
  unit,
  target,
  fill,
}: {
  label: string;
  value: number;
  unit: string;
  target: number;
  fill: string;
}) {
  return (
    <div className="flex min-w-[86px] flex-col gap-1">
      <span className="text-text-tertiary text-[10px] font-semibold uppercase tracking-[0.08em]">
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span className="font-serif text-text text-[17px] font-medium tabular-nums">{value}</span>
        <span className="text-text-secondary text-[11px] font-medium">{unit}</span>
      </div>
      <div className="bg-surface relative h-1 overflow-hidden rounded-full">
        <div className={`h-full ${fill}`} style={{ width: fractionWidth(value, target) }} />
      </div>
    </div>
  );
}
