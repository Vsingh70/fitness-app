"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { AddMealSheet } from "@/components/nutrition/add-meal-sheet";
import { MealSection } from "@/components/nutrition/meal-section";
import { NutritionHero } from "@/components/nutrition/nutrition-hero";
import { api as apiClient } from "@/lib/api/client";
import type { FoodResponse, MealResponse, MealType } from "@/lib/api/nutrition";
import {
  useAddMealItem,
  useCreateMeal,
  useDeleteMealItem,
  useMealsRange,
} from "@/lib/hooks/nutrition";
import { useNutritionTargets, useNutritionToday } from "@/lib/hooks/today";
import { useMe } from "@/lib/hooks/me";
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
  const timezone = me.data?.timezone ?? "UTC";
  const today = useMemo(() => isoDayInTz(new Date().toISOString(), timezone), [timezone]);

  const { fromIso, toIso } = useMemo(() => startEndOfDayUtc(today), [today]);

  const totals = useNutritionToday(today);
  const targets = useNutritionTargets();
  const meals = useMealsRange(fromIso, toIso);
  const createMeal = useCreateMeal();
  const addItem = useAddMealItem();
  const deleteItem = useDeleteMealItem();

  const [sheetMealType, setSheetMealType] = useState<MealType | null>(null);

  // Build a food lookup from any food_ids referenced by current items.
  const referencedFoodIds = useMemo(() => {
    const set = new Set<string>();
    for (const meal of meals.data?.items ?? []) {
      for (const item of meal.items) set.add(item.food_id);
    }
    return [...set].sort();
  }, [meals.data]);

  const foodLookup = useQuery({
    queryKey: ["food-lookup", referencedFoodIds.join(",")],
    queryFn: async () => {
      const out = new Map<string, FoodResponse>();
      await Promise.all(
        referencedFoodIds.map(async (id) => {
          try {
            const food = await apiClient.get<FoodResponse>(`/v1/foods/${id}`);
            out.set(id, food);
          } catch {
            // Ignore — row will fall back to "Food".
          }
        }),
      );
      return out;
    },
    enabled: referencedFoodIds.length > 0,
    staleTime: 5 * 60_000,
  });

  const mealByType = useMemo(() => {
    const map = new Map<MealType, MealResponse | null>();
    for (const type of MEAL_ORDER) map.set(type, null);
    for (const meal of meals.data?.items ?? []) {
      if (!map.get(meal.meal_type)) map.set(meal.meal_type, meal);
    }
    return map;
  }, [meals.data]);

  const onPickFood = async (food: FoodResponse, grams: number) => {
    if (!sheetMealType) return;
    const existing = mealByType.get(sheetMealType);
    const mealId =
      existing?.id ??
      (
        await createMeal.mutateAsync({
          eaten_at: defaultEatenAtForType(today, sheetMealType),
          meal_type: sheetMealType,
        })
      ).id;
    await addItem.mutateAsync({
      mealId,
      body: { food_id: food.id, grams },
    });
    setSheetMealType(null);
  };

  const onDeleteItem = async (itemId: string) => {
    await deleteItem.mutateAsync(itemId);
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

      <NutritionHero totals={totals.data} targets={targets.data} />

      {meals.isLoading ? (
        <p className="text-text-secondary text-sm">Loading meals…</p>
      ) : meals.isError ? (
        <p className="text-destructive text-sm">Could not load meals.</p>
      ) : (
        MEAL_ORDER.map((type) => (
          <MealSection
            key={type}
            type={type}
            meal={mealByType.get(type) ?? null}
            foodLookup={foodLookup.data ?? new Map()}
            onAdd={(t) => setSheetMealType(t)}
            onDelete={onDeleteItem}
          />
        ))
      )}

      <AddMealSheet
        open={sheetMealType !== null}
        mealType={sheetMealType}
        onClose={() => setSheetMealType(null)}
        onPick={onPickFood}
      />
    </div>
  );
}
