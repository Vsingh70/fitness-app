"use client";

import { Plus } from "lucide-react";

import type { RecentFood } from "@/lib/api/nutrition";

interface Props {
  items: RecentFood[];
  /** Log this food in one tap, reproducing its last amount/unit/grams. */
  onLog: (food: RecentFood) => void;
  /** Disables the chips while a one-tap log is in flight. */
  busy?: boolean;
}

function n(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

/** A wrap of tappable food chips that log the user's last logging in one tap. */
export function RecentChips({ items, onLog, busy }: Props) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
        Recent &amp; frequent
      </span>
      <div className="flex flex-wrap gap-2">
        {items.map((food) => (
          <button
            key={food.food_id}
            type="button"
            disabled={busy}
            onClick={() => onLog(food)}
            className="border-border-strong hover:border-text text-text flex items-center gap-2.5 rounded-[var(--radius-pill)] border py-1.5 pr-1.5 pl-3 transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="max-w-[160px] truncate text-[13px] font-medium">{food.name}</span>
            <span className="text-text-secondary font-serif text-[13px] font-semibold tabular-nums">
              {Math.round(n(food.last_kcal))}
            </span>
            <span className="bg-text text-bg grid h-5 w-5 place-items-center rounded-full">
              <Plus className="h-3 w-3" aria-hidden />
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
