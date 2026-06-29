"use client";

import { cn } from "@/lib/cn";
import { kgToDisplay, weightUnitLabel } from "@/lib/utils/format-weight";
import type { components } from "@/lib/api/types";

type UnitSystem = components["schemas"]["UnitSystem"];

const BAR_KG = 20;
const BAR_LB = 45;

const PLATES_KG = [25, 20, 15, 10, 5, 2.5, 1.25];
const PLATES_LB = [45, 35, 25, 10, 5, 2.5];

function computePerSide(target: number, bar: number, plates: number[]): number[] {
  if (!Number.isFinite(target) || target <= bar) return [];
  let remaining = (target - bar) / 2;
  const out: number[] = [];
  for (const p of plates) {
    while (remaining >= p - 1e-6) {
      out.push(p);
      remaining = Math.round((remaining - p) * 1000) / 1000;
    }
  }
  return out;
}

const PLATE_STYLE_KG: Record<number, string> = {
  25: "h-7 w-3.5 bg-text-secondary",
  20: "h-9 w-4 bg-destructive",
  15: "h-8 w-4 bg-warning",
  10: "h-7 w-4 bg-success",
  5: "h-6 w-3.5 bg-text-secondary/70",
  2.5: "h-5 w-3 bg-text-tertiary",
  1.25: "h-4 w-2.5 bg-text-tertiary",
};

const PLATE_STYLE_LB: Record<number, string> = {
  45: "h-9 w-4 bg-text-secondary",
  35: "h-8 w-4 bg-destructive",
  25: "h-7 w-3.5 bg-warning",
  10: "h-7 w-4 bg-success",
  5: "h-6 w-3.5 bg-text-secondary/70",
  2.5: "h-5 w-3 bg-text-tertiary",
};

interface Props {
  targetKg: number | null;
  unit?: UnitSystem;
  unitLabel?: string;
  className?: string;
}

export function PlateMathStrip({ targetKg, unit, unitLabel, className }: Props) {
  if (targetKg === null || targetKg <= 0) return null;

  const imperial = unit === "imperial";
  const displayLabel = unitLabel ?? weightUnitLabel(unit);

  // For imperial: convert target kg → lb, use lb bar and plates
  const bar = imperial ? BAR_LB : BAR_KG;
  const plates = imperial ? PLATES_LB : PLATES_KG;
  const plateStyle = imperial ? PLATE_STYLE_LB : PLATE_STYLE_KG;
  const displayTarget = imperial ? (kgToDisplay(targetKg, "imperial") ?? 0) : targetKg;

  const perSide = computePerSide(displayTarget, bar, plates);
  if (perSide.length === 0) {
    return (
      <div
        className={cn(
          "bg-surface text-text-tertiary flex items-center justify-center gap-2 rounded-[var(--radius-button)] px-3 py-2 text-[11px]",
          className,
        )}
      >
        <span className="font-mono tracking-[0.08em] uppercase">
          Just the bar · {bar} {displayLabel}
        </span>
      </div>
    );
  }

  const each = (displayTarget - bar) / 2;

  return (
    <div
      className={cn(
        "bg-surface flex items-center justify-center gap-1.5 rounded-[var(--radius-button)] px-3 py-2",
        className,
      )}
    >
      <span className="bg-text-tertiary mr-1 h-3 w-1" aria-hidden />
      {[...perSide].reverse().map((p, i) => (
        <span
          key={`l-${i}`}
          className={cn("rounded-[2px]", plateStyle[p] ?? "bg-text-tertiary h-6 w-3")}
          aria-hidden
        />
      ))}
      <span className="bg-text-tertiary mx-1 h-1.5 w-8 rounded-[1px]" aria-hidden />
      {perSide.map((p, i) => (
        <span
          key={`r-${i}`}
          className={cn("rounded-[2px]", plateStyle[p] ?? "bg-text-tertiary h-6 w-3")}
          aria-hidden
        />
      ))}
      <span className="bg-text-tertiary ml-1 h-3 w-1" aria-hidden />
      <span className="text-text-tertiary ml-3 font-mono text-[10px] tracking-[0.08em] uppercase">
        {displayTarget} {displayLabel} · {each.toFixed(each % 1 === 0 ? 0 : 2)} per side
      </span>
    </div>
  );
}
