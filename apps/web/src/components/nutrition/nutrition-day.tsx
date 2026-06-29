"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";

import { CalorieMasthead } from "@/components/nutrition/calorie-masthead";
import { MealList, type MealRowModel } from "@/components/nutrition/meal-list";
import type { PickedIngredient } from "@/components/nutrition/ingredient-picker";
import { NutritionModeControl } from "@/components/nutrition/nutrition-mode-control";
import { QuickAddBar } from "@/components/nutrition/quick-add-bar";
import { RecentChips } from "@/components/nutrition/recent-chips";
import { useToastStore } from "@/components/ui/toast";
import type { MealPlanMeal } from "@/lib/api/meal-plans";
import { getFood } from "@/lib/api/nutrition";
import type { FoodResponse, MealResponse, RecentFood } from "@/lib/api/nutrition";
import { useActivePlan } from "@/lib/hooks/meal-plans";
import { useMe } from "@/lib/hooks/me";
import {
  useAddMealItem,
  useCompletePlannedMeal,
  useCreateMeal,
  useDeleteMeal,
  useDeleteMealItem,
  useMealsRange,
  useRecentFoods,
  useUpdateMealItem,
} from "@/lib/hooks/nutrition";
import { useNutritionTargets, useNutritionToday } from "@/lib/hooks/today";
import { pickedToItemBody } from "@/lib/nutrition/macros";
import { isoDayInTz } from "@/lib/workouts/history";

// The add-meal flow only renders on user action — its own chunk (and the
// search/scan picker it wraps stays lazy too).
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
  // Anchor a new flexible meal to "now" on the viewed day so ordering is stable.
  const [y, m, d] = isoDay.split("-").map((s) => Number.parseInt(s, 10));
  const now = new Date();
  return new Date(
    Date.UTC(y!, m! - 1, d!, now.getUTCHours(), now.getUTCMinutes(), now.getUTCSeconds()),
  ).toISOString();
}

/** The picked food's last logging, mapped to a logged-item body. */
function recentToItemBody(food: RecentFood) {
  return {
    food_id: food.food_id,
    amount: food.last_amount != null ? Number(food.last_amount) : Number(food.last_grams),
    unit: food.last_unit,
    serving_id: food.last_unit === "serving" ? food.last_serving_id : null,
  };
}

/**
 * A meal targeted by the add-meal flow. `mealId` is the backing logged meal
 * when it already exists. When it doesn't, the meal is created on confirm:
 * `planMealId` set → materialize that plan slot; otherwise → a new flexible meal.
 */
type AddTarget = {
  mealId: string | null;
  planMealId: string | null;
  name: string;
  tab: "search" | "scan";
};

export function NutritionDay() {
  const me = useMe();
  const pushToast = useToastStore((s) => s.push);
  const timezone = me.data?.timezone ?? "UTC";
  // The account's tracking preference (04 §Nutrition). Plan mode only takes
  // effect when there's an active plan with slots; otherwise the day presents
  // free-form so nothing logged is ever hidden by the mode.
  const mode: "flexible" | "plan" = me.data?.nutrition_mode === "plan" ? "plan" : "flexible";
  const today = useMemo(() => isoDayInTz(new Date().toISOString(), timezone), [timezone]);
  const { fromIso, toIso } = useMemo(() => startEndOfDayUtc(today), [today]);

  const totals = useNutritionToday(today);
  const targets = useNutritionTargets();
  const meals = useMealsRange(fromIso, toIso);
  const activePlan = useActivePlan(today);
  const recent = useRecentFoods(12);

  const createMeal = useCreateMeal();
  const addItem = useAddMealItem();
  const updateItem = useUpdateMealItem();
  const deleteItem = useDeleteMealItem();
  const deleteMeal = useDeleteMeal();
  const completeMeal = useCompletePlannedMeal();

  const [addTarget, setAddTarget] = useState<AddTarget | null>(null);
  const [loggingRecent, setLoggingRecent] = useState(false);

  const loggedMeals = useMemo(() => meals.data?.items ?? [], [meals.data]);

  // Plan context.
  const resolvedDay = activePlan.data?.resolved_day ?? null;
  const plannedMeals: MealPlanMeal[] = useMemo(
    () => resolvedDay?.template?.meals ?? [],
    [resolvedDay],
  );
  // Plan mode is only "live" when the account is set to it AND there's an active
  // plan with slots to log against. This keeps switching non-destructive: a
  // flexible day with logged meals never disappears just because a plan exists.
  const hasPlan = mode === "plan" && plannedMeals.length > 0;

  const loggedByPlanMealId = useMemo(() => {
    const map = new Map<string, MealResponse>();
    for (const meal of loggedMeals) {
      if (meal.source_plan_meal_id) map.set(meal.source_plan_meal_id, meal);
    }
    return map;
  }, [loggedMeals]);

  // Free-form meals not seeded from a plan slot, ordered by eaten_at. New
  // flexible meals always land here.
  const flexibleMeals = useMemo(
    () =>
      loggedMeals
        .filter((m) => !m.source_plan_meal_id)
        .sort((a, b) => new Date(a.eaten_at).getTime() - new Date(b.eaten_at).getTime()),
    [loggedMeals],
  );

  // In flexible mode every logged meal — including ones seeded from a plan slot
  // on a previous plan-mode day — is re-presented free-form as "Meal 1..n", so a
  // plan→flexible switch never hides what was already logged. Empty plan slots
  // (no items, never logged) are dropped; they carry no data to preserve.
  const allLoggedFlexible = useMemo(
    () =>
      [...loggedMeals].sort(
        (a, b) => new Date(a.eaten_at).getTime() - new Date(b.eaten_at).getTime(),
      ),
    [loggedMeals],
  );

  // Food lookup for every referenced food (names + brands on the rows).
  const referencedFoodIds = useMemo(() => {
    const set = new Set<string>();
    for (const meal of loggedMeals) for (const item of meal.items) set.add(item.food_id);
    return [...set].sort();
  }, [loggedMeals]);

  const foodLookup = useQuery({
    queryKey: ["food-lookup", referencedFoodIds],
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
    placeholderData: keepPreviousData,
  });
  const foods = foodLookup.data ?? new Map<string, FoodResponse>();

  const planId = activePlan.data?.plan.id ?? null;

  // Create a fresh flexible meal (no surfaced meal_type — default "snack").
  const createFlexibleMeal = async (name: string | null): Promise<MealResponse> =>
    createMeal.mutateAsync({
      body: { eaten_at: nowEatenAt(today), meal_type: "snack", name },
      date: today,
    });

  /**
   * Resolve a target to a concrete logged meal id, creating the backing meal if
   * needed: a plan slot is materialized via `complete`; otherwise a fresh
   * flexible meal is created.
   */
  const ensureMealId = async (target: {
    mealId: string | null;
    planMealId: string | null;
  }): Promise<string> => {
    if (target.mealId) return target.mealId;
    if (target.planMealId && planId) {
      const meal = await completeMeal.mutateAsync({
        planId,
        plannedMealId: target.planMealId,
        date: today,
      });
      return meal.id;
    }
    return (await createFlexibleMeal(null)).id;
  };

  // Build the meal rows for the list.
  const rows: MealRowModel[] = useMemo(() => {
    if (hasPlan) {
      const slotRows: MealRowModel[] = [...plannedMeals]
        .sort((a, b) => a.slot_index - b.slot_index)
        .map((slot) => {
          const logged = loggedByPlanMealId.get(slot.id) ?? null;
          return {
            key: logged?.id ?? `slot:${slot.id}`,
            name: slot.name,
            mealId: logged?.id ?? null,
            sourcePlanMealId: slot.id,
            eatenAt: logged?.eaten_at ?? null,
            items: logged?.items ?? [],
            onAddFood: () =>
              setAddTarget({
                mealId: logged?.id ?? null,
                planMealId: slot.id,
                name: slot.name,
                tab: "search",
              }),
          };
        });
      // Non-destructive flexible→plan: free-form meals logged before the switch
      // stay visible as "Meal 1..n" below the plan slots; macros are untouched.
      const carriedRows: MealRowModel[] = flexibleMeals.map((meal, i) => {
        const name = meal.name ?? `Meal ${i + 1}`;
        return {
          key: meal.id,
          name,
          mealId: meal.id,
          sourcePlanMealId: null,
          eatenAt: meal.eaten_at,
          items: meal.items,
          onAddFood: () => setAddTarget({ mealId: meal.id, planMealId: null, name, tab: "search" }),
        };
      });
      return [...slotRows, ...carriedRows];
    }
    // Flexible mode: every logged meal, including plan-seeded ones from a prior
    // plan day, re-presented free-form. Nothing logged is dropped on a switch.
    return allLoggedFlexible.map((meal, i) => {
      const name = meal.name ?? `Meal ${i + 1}`;
      return {
        key: meal.id,
        name,
        mealId: meal.id,
        sourcePlanMealId: null,
        eatenAt: meal.eaten_at,
        items: meal.items,
        onAddFood: () => setAddTarget({ mealId: meal.id, planMealId: null, name, tab: "search" }),
      };
    });
  }, [hasPlan, plannedMeals, loggedByPlanMealId, flexibleMeals, allLoggedFlexible]);

  // The most recent open meal a quick-add / chip should land in (flexible only).
  const newFlexibleName = `Meal ${flexibleMeals.length + 1}`;

  // Open the add flow into a target meal, creating one if needed.
  const openAdd = (tab: "search" | "scan") => {
    if (hasPlan) {
      // Plan mode: drop into the most recent logged meal, else the first slot.
      const recentMeal = [...loggedMeals].sort(
        (a, b) => new Date(b.eaten_at).getTime() - new Date(a.eaten_at).getTime(),
      )[0];
      if (recentMeal) {
        const slot = plannedMeals.find((s) => s.id === recentMeal.source_plan_meal_id);
        setAddTarget({
          mealId: recentMeal.id,
          planMealId: slot?.id ?? null,
          name: slot?.name ?? "meal",
          tab,
        });
      } else {
        const first = [...plannedMeals].sort((a, b) => a.slot_index - b.slot_index)[0];
        setAddTarget({
          mealId: null,
          planMealId: first?.id ?? null,
          name: first?.name ?? "meal",
          tab,
        });
      }
      return;
    }
    const last = flexibleMeals[flexibleMeals.length - 1];
    if (last)
      setAddTarget({ mealId: last.id, planMealId: null, name: last.name ?? newFlexibleName, tab });
    else setAddTarget({ mealId: null, planMealId: null, name: newFlexibleName, tab });
  };

  // Add a freshly created, empty flexible meal and open the add flow into it.
  const addEmptyFlexibleMeal = async () => {
    try {
      const meal = await createFlexibleMeal(null);
      setAddTarget({
        mealId: meal.id,
        planMealId: null,
        name: `Meal ${flexibleMeals.length + 1}`,
        tab: "search",
      });
    } catch {
      pushToast({ kind: "error", message: "Could not add a meal." });
    }
  };

  // One pick from the add flow → log into the target meal (create if needed).
  const onPick = async (picked: PickedIngredient) => {
    if (!addTarget) return;
    try {
      const mealId = await ensureMealId(addTarget);
      await addItem.mutateAsync({ mealId, body: pickedToItemBody(picked), date: today });
      pushToast({ kind: "success", message: "Logged" });
      setAddTarget(null);
    } catch {
      pushToast({ kind: "error", message: "Could not log that food." });
    }
  };

  // One-tap recent chip → reproduce the last logging into a sensible meal.
  const logRecent = async (food: RecentFood) => {
    setLoggingRecent(true);
    try {
      let mealId: string;
      if (hasPlan) {
        const recentMeal = [...loggedMeals].sort(
          (a, b) => new Date(b.eaten_at).getTime() - new Date(a.eaten_at).getTime(),
        )[0];
        if (recentMeal) {
          mealId = recentMeal.id;
        } else {
          // No logged meal yet — materialize the first plan slot to log into.
          const first = [...plannedMeals].sort((a, b) => a.slot_index - b.slot_index)[0];
          mealId = await ensureMealId({ mealId: null, planMealId: first?.id ?? null });
        }
      } else {
        const last = flexibleMeals[flexibleMeals.length - 1];
        mealId = last ? last.id : (await createFlexibleMeal(null)).id;
      }
      await addItem.mutateAsync({ mealId, body: recentToItemBody(food), date: today });
      pushToast({ kind: "success", message: `Logged ${food.name}` });
    } catch {
      pushToast({ kind: "error", message: "Could not log that food." });
    } finally {
      setLoggingRecent(false);
    }
  };

  const headerKicker = new Date().toLocaleDateString(undefined, {
    timeZone: timezone,
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-[var(--space-section)] pb-10">
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div>
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
            {headerKicker}
          </span>
          <div className="mt-1 flex items-center gap-4">
            <h1 className="text-text font-serif text-[clamp(1.75rem,1.5rem+0.9vw,2rem)] font-medium tracking-tight">
              Nutrition
            </h1>
            <NutritionModeControl mode={mode} />
            <Link
              href="/nutrition/plans"
              className="text-text-secondary hover:text-text text-[11px] font-semibold tracking-[0.08em] uppercase transition-colors"
            >
              Meal plans
            </Link>
            {activePlan.data?.plan && (
              <Link
                href={`/nutrition/plans/${activePlan.data.plan.id}`}
                className="border-border bg-surface text-text-secondary hover:text-text inline-flex h-[22px] max-w-[160px] items-center truncate rounded-[var(--radius-pill)] border px-2.5 text-[10px] font-semibold tracking-[0.08em] uppercase transition-colors"
                title={activePlan.data.plan.name}
              >
                {activePlan.data.plan.name}
              </Link>
            )}
          </div>
        </div>
        <nav
          aria-label="Day or week view"
          className="border-border flex gap-[18px] border-b text-[11px] font-semibold tracking-[0.08em] uppercase"
        >
          <span className="border-text text-text -mb-px border-b-[1.5px] pb-[7px]">Day</span>
          <Link
            href="/nutrition/trends"
            className="text-text-secondary hover:text-text -mb-px border-b-[1.5px] border-transparent pb-[7px]"
          >
            Week
          </Link>
        </nav>
      </header>

      <CalorieMasthead totals={totals.data} targets={targets.data} />

      {/* Quick-add cluster: the hero search and its recent chips read as one
          input group, so they sit tighter than the section rhythm. */}
      <div className="flex flex-col gap-3.5">
        <QuickAddBar onAdd={() => openAdd("search")} onScan={() => openAdd("scan")} />
        <RecentChips items={recent.data?.items ?? []} onLog={logRecent} busy={loggingRecent} />
      </div>

      {meals.isLoading ? (
        <p className="text-text-secondary text-sm">Loading meals…</p>
      ) : meals.isError ? (
        <p className="text-destructive text-sm">Could not load meals.</p>
      ) : rows.length === 0 ? (
        <p className="text-text-tertiary py-2 text-[13px]">
          No meals yet. Use the search bar above to log your first meal.
        </p>
      ) : (
        <MealList
          rows={rows}
          foodLookup={foods}
          onDeleteItem={(itemId) => deleteItem.mutate({ itemId, date: today })}
          onEditItem={(itemId, body) => updateItem.mutate({ itemId, body, date: today })}
          onDeleteMeal={(mealId, scope) => deleteMeal.mutate({ mealId, scope, date: today })}
        />
      )}

      {/* Flexible mode adds unlimited meals; plan mode's count is fixed. */}
      {!hasPlan ? (
        <button
          type="button"
          onClick={addEmptyFlexibleMeal}
          disabled={createMeal.isPending}
          className="border-border-strong text-text-tertiary hover:border-text hover:text-text w-full rounded-[var(--radius-button)] border border-dashed py-3 text-[13px] font-medium transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-50"
        >
          + Add meal
        </button>
      ) : null}

      <AddMealSheet
        open={addTarget !== null}
        mealName={addTarget?.name ?? "meal"}
        initialTab={addTarget?.tab ?? "search"}
        onClose={() => setAddTarget(null)}
        onPick={onPick}
      />
    </div>
  );
}
