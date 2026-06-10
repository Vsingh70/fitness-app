"use client";

import { cn } from "@/lib/cn";
import type { PeriodizationMode } from "@/lib/programs/types";

const OPTIONS: { mode: PeriodizationMode; title: string; helper: string }[] = [
  {
    mode: "block",
    title: "Periodized block",
    helper: "Ramps over a fixed mesocycle with planned deloads, then you start a fresh block.",
  },
  {
    mode: "continuous",
    title: "Just keep progressing",
    helper: "No end date and no scheduled deloads. Progression keeps applying every session.",
  },
];

interface Props {
  mode: PeriodizationMode;
  onChange: (mode: PeriodizationMode) => void;
  /** Render the reactive-deload toggle when continuous. */
  autoDeloadOnStall?: boolean;
  onAutoDeloadOnStallChange?: (value: boolean) => void;
  disabled?: boolean;
}

/**
 * Two-option lifecycle picker for program setup: a finite periodized block vs an
 * open-ended continuous program. In continuous mode it also exposes the reactive
 * per-lift deload toggle bound to `auto_deload_on_stall`.
 */
export function PeriodizationControl({
  mode,
  onChange,
  autoDeloadOnStall,
  onAutoDeloadOnStallChange,
  disabled,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
        How should this program run?
      </span>
      <div className="grid gap-2.5 sm:grid-cols-2">
        {OPTIONS.map((opt) => {
          const selected = mode === opt.mode;
          return (
            <button
              key={opt.mode}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onChange(opt.mode)}
              className={cn(
                "flex flex-col gap-1 rounded-[var(--radius-card)] border p-3.5 text-left",
                "transition-[border-color,background-color] duration-150 ease-out",
                "disabled:cursor-not-allowed disabled:opacity-60",
                selected
                  ? "border-accent bg-accent-soft"
                  : "border-border-strong bg-surface-elevated hover:border-text",
              )}
            >
              <span className="text-text text-sm font-semibold">{opt.title}</span>
              <span className="text-text-secondary text-[12px] leading-snug">{opt.helper}</span>
            </button>
          );
        })}
      </div>

      {mode === "continuous" && onAutoDeloadOnStallChange ? (
        <label className="border-border bg-surface-elevated flex cursor-pointer items-start gap-3 rounded-[var(--radius-card)] border p-3.5">
          <input
            type="checkbox"
            className="accent-accent mt-0.5 h-4 w-4"
            checked={autoDeloadOnStall ?? true}
            disabled={disabled}
            onChange={(e) => onAutoDeloadOnStallChange(e.target.checked)}
          />
          <span className="flex flex-col gap-0.5">
            <span className="text-text text-sm font-semibold">Suggest a deload when a lift stalls</span>
            <span className="text-text-secondary text-[12px] leading-snug">
              We watch for stalls and offer a deload for just that lift, never the whole program.
            </span>
          </span>
        </label>
      ) : null}
    </div>
  );
}
