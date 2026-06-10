"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";

import { MealBuilderSheet } from "@/components/nutrition/meal-builder-sheet";
import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { num, trackingLine, type MealPlanMeal, type TrackingMode } from "@/lib/api/meal-plans";
import type { MealSwap } from "@/lib/api/nutrition";
import { pickedToItemBody } from "@/lib/nutrition/macros";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Planned meals on today's resolved day, offered as swap targets. */
  plannedMeals: MealPlanMeal[];
  /** The plan meal currently backing this logged meal (excluded from the list). */
  currentPlanMealId: string | null;
  trackingMode: TrackingMode;
  onSwap: (body: MealSwap) => Promise<void> | void;
  pending?: boolean;
}

/**
 * Swap a logged meal for a different planned meal, or build a fresh meal from the
 * shared ingredient picker. Both paths produce a {@link MealSwap} body.
 */
export function SwapMealSheet({
  open,
  onClose,
  plannedMeals,
  currentPlanMealId,
  trackingMode,
  onSwap,
  pending = false,
}: Props) {
  const [building, setBuilding] = useState(false);

  const options = plannedMeals.filter((m) => m.id !== currentPlanMealId);

  return (
    <>
      <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title="Swap meal">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
              Use another planned meal
            </span>
            {options.length === 0 ? (
              <p className="text-text-tertiary text-[13px]">
                No other planned meals to swap in today.
              </p>
            ) : (
              <div className="border-border bg-surface rounded-[var(--radius-card)] border">
                {options.map((meal) => (
                  <button
                    key={meal.id}
                    type="button"
                    disabled={pending}
                    onClick={() => onSwap({ plan_meal_id: meal.id })}
                    className="border-border hover:bg-surface-elevated grid w-full grid-cols-[1fr_auto] items-center gap-3 border-b px-4 py-3 text-left transition-colors duration-150 ease-out last:border-b-0 disabled:opacity-50"
                  >
                    <div className="min-w-0">
                      <div className="text-text truncate text-sm font-medium">{meal.name}</div>
                      <div className="text-text-tertiary mt-0.5 text-[11px]">
                        {meal.items.length} item{meal.items.length === 1 ? "" : "s"}
                        {num(meal.totals.kcal) > 0
                          ? ` · ${trackingLine(meal.totals, trackingMode)}`
                          : ""}
                      </div>
                    </div>
                    {pending ? (
                      <Loader2 className="text-text-tertiary h-4 w-4 animate-spin" aria-hidden />
                    ) : null}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="border-border border-t pt-4">
            <Button variant="secondary" size="sm" onClick={() => setBuilding(true)}>
              Build a fresh meal instead
            </Button>
          </div>
        </div>
      </Sheet>

      <MealBuilderSheet
        open={building}
        swapMode
        saving={pending}
        onClose={() => setBuilding(false)}
        onSave={async ({ ingredients }) => {
          await onSwap({ items: ingredients.map(pickedToItemBody) });
          setBuilding(false);
        }}
      />
    </>
  );
}
