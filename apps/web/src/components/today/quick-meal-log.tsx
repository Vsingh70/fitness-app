"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";

import { CalorieMasthead } from "@/components/nutrition/calorie-masthead";
import type { PickedIngredient } from "@/components/nutrition/ingredient-picker";
import { QuickAddBar } from "@/components/nutrition/quick-add-bar";
import { useToastStore } from "@/components/ui/toast";
import type { MealResponse } from "@/lib/api/nutrition";
import { useMe } from "@/lib/hooks/me";
import { useActivePlan } from "@/lib/hooks/meal-plans";
import {
  useAddMealItem,
  useCompletePlannedMeal,
  useCreateMeal,
  useMealsRange,
} from "@/lib/hooks/nutrition";
import { useNutritionTargets, useNutritionToday } from "@/lib/hooks/today";
import { pickedToItemBody } from "@/lib/nutrition/macros";
import { isoDayInTz } from "@/lib/workouts/history";

// The picker chunk only loads when the user opens the add flow.
const AddMealSheet = dynamic(
  () => import("@/components/nutrition/add-meal-sheet").then((m) => m.AddMealSheet),
  { ssr: false },
);

function startEndOfDayUtc(isoDay: string): { fromIso: string; toIso: string } {
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  const start = new Date(Date.UTC(y!, m! - 1, d!, 0, 0, 0));
  const end = new Date(Date.UTC(y!, m! - 1, d!, 23, 59, 59));
  return { fromIso: start.toISOString(), toIso: end.toISOString() };
}

function nowEatenAt(isoDay: string): string {
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  const now = new Date();
  return new Date(
    Date.UTC(y!, m! - 1, d!, now.getUTCHours(), now.getUTCMinutes(), now.getUTCSeconds()),
  ).toISOString();
}

/**
 * The Today command center's quick meal-log: the calorie masthead plus the
 * nutrition quick-add bar. Picking a food logs it into today's most recent
 * meal (or a fresh flexible meal / the first plan slot when none exists), then
 * the full Nutrition surface is one tap away. Reuses the nutrition hooks and
 * the shared {@link QuickAddBar} / add-meal flow rather than re-implementing.
 */
export function QuickMealLog() {
  const me = useMe();
  const pushToast = useToastStore((s) => s.push);
  const timezone = me.data?.timezone ?? "UTC";
  const today = useMemo(() => isoDayInTz(new Date().toISOString(), timezone), [timezone]);
  const { fromIso, toIso } = useMemo(() => startEndOfDayUtc(today), [today]);

  const totals = useNutritionToday(today);
  const targets = useNutritionTargets();
  const meals = useMealsRange(fromIso, toIso);
  const activePlan = useActivePlan(today);

  const createMeal = useCreateMeal();
  const addItem = useAddMealItem();
  const completeMeal = useCompletePlannedMeal();

  const [tab, setTab] = useState<"search" | "scan" | null>(null);

  const loggedMeals = useMemo(() => meals.data?.items ?? [], [meals.data]);
  const plannedMeals = activePlan.data?.resolved_day?.template?.meals ?? [];
  const planId = activePlan.data?.plan.id ?? null;
  const hasPlan = plannedMeals.length > 0;

  // Resolve the meal a quick-add should land in, creating one if needed:
  // plan mode → most recent logged meal, else materialize the first slot;
  // flexible → most recent flexible meal, else a fresh one.
  const resolveMealId = async (): Promise<string> => {
    if (hasPlan) {
      const recentMeal = [...loggedMeals].sort(
        (a, b) => new Date(b.eaten_at).getTime() - new Date(a.eaten_at).getTime(),
      )[0];
      if (recentMeal) return recentMeal.id;
      const first = [...plannedMeals].sort((a, b) => a.slot_index - b.slot_index)[0];
      if (first && planId) {
        const meal: MealResponse = await completeMeal.mutateAsync({
          planId,
          plannedMealId: first.id,
          date: today,
        });
        return meal.id;
      }
    }
    const flexible = loggedMeals
      .filter((m) => !m.source_plan_meal_id)
      .sort((a, b) => new Date(a.eaten_at).getTime() - new Date(b.eaten_at).getTime());
    const last = flexible[flexible.length - 1];
    if (last) return last.id;
    const created = await createMeal.mutateAsync({
      body: { eaten_at: nowEatenAt(today), meal_type: "snack", name: null },
      date: today,
    });
    return created.id;
  };

  const onPick = async (picked: PickedIngredient) => {
    try {
      const mealId = await resolveMealId();
      await addItem.mutateAsync({ mealId, body: pickedToItemBody(picked), date: today });
      pushToast({ kind: "success", message: "Logged" });
      setTab(null);
    } catch {
      pushToast({ kind: "error", message: "Could not log that food." });
    }
  };

  return (
    <div className="border-border bg-surface-elevated flex flex-col gap-5 rounded-[var(--radius-card)] border p-6">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-text-secondary text-[13px] font-semibold tracking-[0.1em] uppercase">
          Nutrition
        </span>
        <Link
          href="/nutrition"
          className="text-accent text-[12px] font-medium hover:brightness-110"
        >
          Open log →
        </Link>
      </div>
      <CalorieMasthead totals={totals.data} targets={targets.data} />
      <QuickAddBar onAdd={() => setTab("search")} onScan={() => setTab("scan")} />
      <AddMealSheet
        open={tab !== null}
        mealName="meal"
        initialTab={tab ?? "search"}
        onClose={() => setTab(null)}
        onPick={onPick}
      />
    </div>
  );
}
