"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { DeleteMealSheet } from "@/components/nutrition/delete-meal-sheet";
import { EditMealSheet } from "@/components/nutrition/edit-meal-sheet";
import { MealBuilderSheet } from "@/components/nutrition/meal-builder-sheet";
import { MealSection } from "@/components/nutrition/meal-section";
import { NutritionHero } from "@/components/nutrition/nutrition-hero";
import { PlannedMealList } from "@/components/nutrition/planned-meal-list";
import { SwapMealSheet } from "@/components/nutrition/swap-meal-sheet";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import type { MealPlanMeal, TrackingMode } from "@/lib/api/meal-plans";
import { getFood } from "@/lib/api/nutrition";
import type {
  DeleteScope,
  FoodResponse,
  MealItemUpdate,
  MealResponse,
  MealSwap,
  MealType,
} from "@/lib/api/nutrition";
import {
  useCompletePlannedMeal,
  useCreateMeal,
  useAddMealItem,
  useDeleteMealItem,
  useDeleteMeal,
  useMealsRange,
  useSwapMeal,
  useUpdateMealItem,
} from "@/lib/hooks/nutrition";
import { useActivePlan } from "@/lib/hooks/meal-plans";
import { useNutritionTargets, useNutritionToday } from "@/lib/hooks/today";
import { useMe } from "@/lib/hooks/me";
import { pickedToItemBody } from "@/lib/nutrition/macros";
import { isoDayInTz } from "@/lib/workouts/history";

const MEAL_ORDER: MealType[] = ["breakfast", "lunch", "dinner", "snack"];

function startEndOfDayUtc(isoDay: string): { fromIso: string; toIso: string } {
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  const start = new Date(Date.UTC(y!, m! - 1, d!, 0, 0, 0));
  const end = new Date(Date.UTC(y!, m! - 1, d!, 23, 59, 59));
  return { fromIso: start.toISOString(), toIso: end.toISOString() };
}

function defaultEatenAtForType(isoDay: string, type: MealType): string {
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  const hours: Record<MealType, number> = {
    breakfast: 8,
    lunch: 13,
    dinner: 19,
    snack: 16,
  };
  return new Date(Date.UTC(y!, m! - 1, d!, hours[type], 0, 0)).toISOString();
}

export default function NutritionPage() {
  const me = useMe();
  const pushToast = useToastStore((s) => s.push);
  const timezone = me.data?.timezone ?? "UTC";
  const today = useMemo(() => isoDayInTz(new Date().toISOString(), timezone), [timezone]);
  const { fromIso, toIso } = useMemo(() => startEndOfDayUtc(today), [today]);

  const totals = useNutritionToday(today);
  const targets = useNutritionTargets();
  const meals = useMealsRange(fromIso, toIso);
  const activePlan = useActivePlan(today);

  const completeMeal = useCompletePlannedMeal();
  const createMeal = useCreateMeal();
  const addItem = useAddMealItem();
  const updateItem = useUpdateMealItem();
  const deleteItem = useDeleteMealItem();
  const deleteMeal = useDeleteMeal();
  const swapMeal = useSwapMeal();

  // Sheet/dialog state.
  const [trackOpen, setTrackOpen] = useState(false);
  const [editMeal, setEditMeal] = useState<MealResponse | null>(null);
  const [swapTarget, setSwapTarget] = useState<{ meal: MealResponse; planMealId: string } | null>(
    null,
  );
  const [deleteTarget, setDeleteTarget] = useState<{
    meal: MealResponse;
    name: string;
    fromPlan: boolean;
  } | null>(null);
  const [completingId, setCompletingId] = useState<string | null>(null);

  const loggedMeals = useMemo(() => meals.data?.items ?? [], [meals.data]);

  // Plan context: resolved day + its planned meals + tracking mode.
  const resolvedDay = activePlan.data?.resolved_day ?? null;
  const plannedMeals: MealPlanMeal[] = resolvedDay?.template?.meals ?? [];
  const trackingMode: TrackingMode =
    totals.data?.tracking_mode ?? resolvedDay?.tracking_mode ?? "macros_and_calories";

  // Logged meals that came from a planned slot, keyed by source_plan_meal_id.
  const loggedByPlanMealId = useMemo(() => {
    const map = new Map<string, MealResponse>();
    for (const meal of loggedMeals) {
      if (meal.source_plan_meal_id) map.set(meal.source_plan_meal_id, meal);
    }
    return map;
  }, [loggedMeals]);

  // Off-plan logged meals (no source plan meal), grouped by meal_type for the
  // flexible-tracking section.
  const offPlanByType = useMemo(() => {
    const map = new Map<MealType, MealResponse | null>();
    for (const type of MEAL_ORDER) map.set(type, null);
    for (const meal of loggedMeals) {
      if (meal.source_plan_meal_id) continue;
      if (!map.get(meal.meal_type)) map.set(meal.meal_type, meal);
    }
    return map;
  }, [loggedMeals]);

  // Food lookup for any food referenced by today's logged items.
  const referencedFoodIds = useMemo(() => {
    const set = new Set<string>();
    for (const meal of loggedMeals) for (const item of meal.items) set.add(item.food_id);
    return [...set].sort();
  }, [loggedMeals]);

  const foodLookup = useQuery({
    queryKey: ["food-lookup", referencedFoodIds.join(",")],
    queryFn: async () => {
      const out = new Map<string, FoodResponse>();
      await Promise.all(
        referencedFoodIds.map(async (id) => {
          try {
            out.set(id, await getFood(id));
          } catch {
            // Ignore — row falls back to "Food".
          }
        }),
      );
      return out;
    },
    enabled: referencedFoodIds.length > 0,
    staleTime: 5 * 60_000,
  });
  const foods = foodLookup.data ?? new Map<string, FoodResponse>();

  const planId = activePlan.data?.plan.id ?? null;
  const hasPlannedMeals = plannedMeals.length > 0;

  // Handlers ---------------------------------------------------------------
  const onComplete = (plannedMealId: string) => {
    if (!planId) return;
    setCompletingId(plannedMealId);
    completeMeal.mutate(
      { planId, plannedMealId, date: today },
      {
        onSuccess: () => pushToast({ kind: "success", message: "Meal logged" }),
        onError: () => pushToast({ kind: "error", message: "Could not complete meal." }),
        onSettled: () => setCompletingId(null),
      },
    );
  };

  const onSaveEditItem = async (itemId: string, body: MealItemUpdate) => {
    try {
      await updateItem.mutateAsync({ itemId, body });
      pushToast({ kind: "success", message: "Serving updated" });
    } catch {
      pushToast({ kind: "error", message: "Could not update serving." });
    }
  };

  const onSwap = async (body: MealSwap) => {
    if (!swapTarget) return;
    try {
      await swapMeal.mutateAsync({ mealId: swapTarget.meal.id, body });
      pushToast({ kind: "success", message: "Meal swapped" });
      setSwapTarget(null);
    } catch {
      pushToast({ kind: "error", message: "Could not swap meal." });
    }
  };

  const onConfirmDelete = async (scope: DeleteScope) => {
    if (!deleteTarget) return;
    try {
      await deleteMeal.mutateAsync({ mealId: deleteTarget.meal.id, scope });
      pushToast({
        kind: "info",
        message: scope === "forever" ? "Removed from plan" : "Meal deleted for today",
      });
      setDeleteTarget(null);
    } catch {
      pushToast({ kind: "error", message: "Could not delete meal." });
    }
  };

  // Flexible tracking: create the meal, then post each item.
  const onTrackSave = async ({
    mealType,
    eatenAt,
    ingredients,
  }: {
    mealType: MealType;
    eatenAt: string | null;
    ingredients: Parameters<typeof pickedToItemBody>[0][];
  }) => {
    try {
      const meal = await createMeal.mutateAsync({
        eaten_at: eatenAt ?? defaultEatenAtForType(today, mealType),
        meal_type: mealType,
      });
      for (const ing of ingredients) {
        await addItem.mutateAsync({ mealId: meal.id, body: pickedToItemBody(ing) });
      }
      pushToast({ kind: "success", message: "Meal tracked" });
      setTrackOpen(false);
    } catch {
      pushToast({ kind: "error", message: "Could not track meal." });
    }
  };

  const headerKicker = new Date().toLocaleDateString(undefined, {
    timeZone: timezone,
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 pb-10">
      <header className="flex items-end justify-between gap-4">
        <div>
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
            {headerKicker}
          </span>
          <h1 className="mt-1 font-serif text-[32px] font-medium tracking-tight">Nutrition</h1>
        </div>
        <Link
          href="/nutrition/plans"
          className="text-text-secondary hover:text-text border-border-strong inline-flex h-[32px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.08em] uppercase"
        >
          Meal plans
        </Link>
      </header>

      <NutritionHero
        totals={totals.data}
        targets={targets.data}
        trackingMode={trackingMode}
        adherence={totals.data?.adherence}
      />

      {/* Plan-active checklist */}
      {hasPlannedMeals ? (
        <section className="flex flex-col gap-2.5">
          <div className="flex items-baseline justify-between px-1">
            <h2 className="text-text text-sm font-semibold">
              {activePlan.data?.plan.name ?? "Today's plan"}
            </h2>
            {totals.data?.adherence && totals.data.adherence.planned_meals > 0 ? (
              <span className="text-text-secondary text-[12px] tabular-nums">
                {totals.data.adherence.completed_meals} of {totals.data.adherence.planned_meals}{" "}
                complete
              </span>
            ) : null}
          </div>
          <PlannedMealList
            plannedMeals={plannedMeals}
            loggedByPlanMealId={loggedByPlanMealId}
            trackingMode={trackingMode}
            completingId={completingId}
            onComplete={onComplete}
            onEdit={(meal) => setEditMeal(meal)}
            onSwap={(meal, planMealId) => setSwapTarget({ meal, planMealId })}
            onDelete={(meal, name, fromPlan) => setDeleteTarget({ meal, name, fromPlan })}
          />
        </section>
      ) : null}

      {/* Flexible tracking */}
      <div className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-text text-sm font-semibold">
            {hasPlannedMeals ? "Off-plan meals" : "Today's meals"}
          </h2>
          <Button size="sm" onClick={() => setTrackOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" aria-hidden /> Track a meal
          </Button>
        </div>

        {meals.isLoading ? (
          <p className="text-text-secondary text-sm">Loading meals…</p>
        ) : meals.isError ? (
          <p className="text-destructive text-sm">Could not load meals.</p>
        ) : (
          MEAL_ORDER.map((type) => {
            const meal = offPlanByType.get(type) ?? null;
            // With a plan active, hide empty off-plan slots to keep the list tidy.
            if (hasPlannedMeals && !meal) return null;
            return (
              <MealSection
                key={type}
                type={type}
                meal={meal}
                foodLookup={foods}
                onAdd={() => setTrackOpen(true)}
                onDelete={(itemId) => deleteItem.mutate(itemId)}
              />
            );
          })
        )}
      </div>

      <MealBuilderSheet
        open={trackOpen}
        onClose={() => setTrackOpen(false)}
        onSave={onTrackSave}
        saving={createMeal.isPending || addItem.isPending}
      />

      <EditMealSheet
        open={editMeal !== null}
        meal={editMeal}
        foodLookup={foods}
        onClose={() => setEditMeal(null)}
        onSaveItem={onSaveEditItem}
        pending={updateItem.isPending}
      />

      <SwapMealSheet
        open={swapTarget !== null}
        onClose={() => setSwapTarget(null)}
        plannedMeals={plannedMeals}
        currentPlanMealId={swapTarget?.planMealId ?? null}
        trackingMode={trackingMode}
        onSwap={onSwap}
        pending={swapMeal.isPending}
      />

      <DeleteMealSheet
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        mealName={deleteTarget?.name ?? "this meal"}
        fromPlan={deleteTarget?.fromPlan ?? false}
        onDelete={onConfirmDelete}
        pending={deleteMeal.isPending}
      />
    </div>
  );
}
