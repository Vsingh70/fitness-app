"use client";

import { Check, Loader2, MoreHorizontal } from "lucide-react";
import { useState } from "react";

import {
  num,
  trackingLine,
  type MealPlanMeal,
  type TrackingMode,
} from "@/lib/api/meal-plans";
import type { MealResponse } from "@/lib/api/nutrition";
import { cn } from "@/lib/cn";

interface Props {
  plannedMeals: MealPlanMeal[];
  /** Logged meals for today, used to find the one backing each planned meal. */
  loggedByPlanMealId: Map<string, MealResponse>;
  trackingMode: TrackingMode;
  /** Plan meal id currently being completed, for the spinner. */
  completingId: string | null;
  onComplete: (plannedMealId: string) => void;
  onEdit: (meal: MealResponse) => void;
  onSwap: (meal: MealResponse, planMealId: string) => void;
  onDelete: (meal: MealResponse, name: string, fromPlan: boolean) => void;
}

function fmtTime(time: string | null): string | null {
  if (!time) return null;
  const [h, m] = time.split(":");
  if (h == null) return null;
  const hour = Number.parseInt(h, 10);
  const ampm = hour >= 12 ? "PM" : "AM";
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  return `${h12}:${m ?? "00"} ${ampm}`;
}

export function PlannedMealList({
  plannedMeals,
  loggedByPlanMealId,
  trackingMode,
  completingId,
  onComplete,
  onEdit,
  onSwap,
  onDelete,
}: Props) {
  const sorted = [...plannedMeals].sort((a, b) => a.slot_index - b.slot_index);

  return (
    <section className="flex flex-col gap-2">
      {sorted.map((planned) => {
        const logged = loggedByPlanMealId.get(planned.id) ?? null;
        return (
          <PlannedMealRow
            key={planned.id}
            planned={planned}
            logged={logged}
            trackingMode={trackingMode}
            completing={completingId === planned.id}
            onComplete={() => onComplete(planned.id)}
            onEdit={() => logged && onEdit(logged)}
            onSwap={() => logged && onSwap(logged, planned.id)}
            onDelete={() => logged && onDelete(logged, planned.name, true)}
          />
        );
      })}
    </section>
  );
}

function PlannedMealRow({
  planned,
  logged,
  trackingMode,
  completing,
  onComplete,
  onEdit,
  onSwap,
  onDelete,
}: {
  planned: MealPlanMeal;
  logged: MealResponse | null;
  trackingMode: TrackingMode;
  completing: boolean;
  onComplete: () => void;
  onEdit: () => void;
  onSwap: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const done = logged !== null;
  const time = fmtTime(planned.planned_time);
  const macroLine = num(planned.totals.kcal) > 0 ? trackingLine(planned.totals, trackingMode) : null;

  return (
    <div
      className={cn(
        "border-border bg-surface-elevated flex items-center gap-3 rounded-[var(--radius-card)] border px-4 py-3",
        done && "border-success/40",
      )}
    >
      <button
        type="button"
        onClick={onComplete}
        disabled={done || completing}
        aria-label={done ? `${planned.name} complete` : `Mark ${planned.name} complete`}
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors duration-150 ease-out",
          done
            ? "border-success bg-success text-white"
            : "border-border-strong text-text-tertiary hover:border-accent hover:text-accent",
        )}
      >
        {completing ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : done ? (
          <Check className="h-4 w-4" aria-hidden />
        ) : (
          <span className="text-[10px] font-semibold uppercase">go</span>
        )}
      </button>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={cn("text-text truncate text-sm font-medium", done && "text-text-secondary")}>
            {planned.name}
          </span>
          {time ? <span className="text-text-tertiary text-[11px]">{time}</span> : null}
        </div>
        <div className="text-text-tertiary mt-0.5 text-[11px] tabular-nums">
          {planned.items.length} item{planned.items.length === 1 ? "" : "s"}
          {macroLine ? ` · ${macroLine}` : ""}
        </div>
      </div>

      {done ? (
        <div className="relative">
          <button
            type="button"
            aria-label="Meal options"
            onClick={() => setMenuOpen((v) => !v)}
            className="text-text-tertiary hover:text-text flex h-8 w-8 items-center justify-center"
          >
            <MoreHorizontal className="h-4 w-4" aria-hidden />
          </button>
          {menuOpen ? (
            <>
              <button
                type="button"
                aria-hidden
                tabIndex={-1}
                onClick={() => setMenuOpen(false)}
                className="fixed inset-0 z-10 cursor-default"
              />
              <div className="border-border bg-surface-elevated absolute right-0 z-20 mt-1 w-36 overflow-hidden rounded-[var(--radius-card)] border shadow-lg">
                <MenuItem
                  label="Edit"
                  onClick={() => {
                    setMenuOpen(false);
                    onEdit();
                  }}
                />
                <MenuItem
                  label="Swap"
                  onClick={() => {
                    setMenuOpen(false);
                    onSwap();
                  }}
                />
                <MenuItem
                  label="Delete"
                  destructive
                  onClick={() => {
                    setMenuOpen(false);
                    onDelete();
                  }}
                />
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function MenuItem({
  label,
  onClick,
  destructive,
}: {
  label: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "hover:bg-surface block w-full px-3 py-2 text-left text-[13px]",
        destructive ? "text-destructive" : "text-text",
      )}
    >
      {label}
    </button>
  );
}
