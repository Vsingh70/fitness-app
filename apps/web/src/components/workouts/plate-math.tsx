"use client";

import { cn } from "@/lib/cn";

const BAR_KG = 20;
const PLATES_KG = [25, 20, 15, 10, 5, 2.5, 1.25];

function computePerSide(target: number, barKg = BAR_KG): number[] {
  if (!Number.isFinite(target) || target <= barKg) return [];
  let remaining = (target - barKg) / 2;
  const out: number[] = [];
  for (const p of PLATES_KG) {
    while (remaining >= p - 1e-6) {
      out.push(p);
      remaining = Math.round((remaining - p) * 1000) / 1000;
    }
  }
  return out;
}

const PLATE_STYLE: Record<number, string> = {
  25: "h-7 w-3.5 bg-text-secondary",
  20: "h-9 w-4 bg-destructive",
  15: "h-8 w-4 bg-warning",
  10: "h-7 w-4 bg-success",
  5: "h-6 w-3.5 bg-text-secondary/70",
  2.5: "h-5 w-3 bg-text-tertiary",
  1.25: "h-4 w-2.5 bg-text-tertiary",
};

interface Props {
  targetKg: number | null;
  unitLabel?: string;
  className?: string;
}

export function PlateMathStrip({ targetKg, unitLabel = "kg", className }: Props) {
  if (targetKg === null || targetKg <= 0) return null;

  const perSide = computePerSide(targetKg);
  if (perSide.length === 0) {
    return (
      <div
        className={cn(
          "bg-surface text-text-tertiary flex items-center justify-center gap-2 rounded-[var(--radius-button)] px-3 py-2 text-[11px]",
          className,
        )}
      >
        <span className="font-mono tracking-[0.08em] uppercase">
          Just the bar · {BAR_KG} {unitLabel}
        </span>
      </div>
    );
  }

  const each = (targetKg - BAR_KG) / 2;

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
          className={cn("rounded-[2px]", PLATE_STYLE[p] ?? "bg-text-tertiary h-6 w-3")}
          aria-hidden
        />
      ))}
      <span className="bg-text-tertiary mx-1 h-1.5 w-8 rounded-[1px]" aria-hidden />
      {perSide.map((p, i) => (
        <span
          key={`r-${i}`}
          className={cn("rounded-[2px]", PLATE_STYLE[p] ?? "bg-text-tertiary h-6 w-3")}
          aria-hidden
        />
      ))}
      <span className="bg-text-tertiary ml-1 h-3 w-1" aria-hidden />
      <span className="text-text-tertiary ml-3 font-mono text-[10px] tracking-[0.08em] uppercase">
        {targetKg} {unitLabel} · {each.toFixed(each % 1 === 0 ? 0 : 2)} per side
      </span>
    </div>
  );
}
