"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock, Plus, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";

import { IngredientPicker, type PickedIngredient } from "@/components/nutrition/ingredient-picker";
import { useToastStore } from "@/components/ui/toast";
import {
  dayRoleLabel,
  num,
  trackingLine,
  type MealPlan,
  type MealPlanDay,
  type MealPlanItem,
  type MealPlanMeal,
} from "@/lib/api/meal-plans";
import { getFood, type FoodResponse } from "@/lib/api/nutrition";
import {
  useAddPlanItem,
  useAddPlanMeal,
  useDeletePlanItem,
  useDeletePlanMeal,
  useUpdatePlanMeal,
} from "@/lib/hooks/meal-plans";

type FoodNames = Map<string, string>;

interface Props {
  plan: MealPlan;
  day: MealPlanDay;
}

export function PlanDayEditor({ plan, day }: Props) {
  const pushToast = useToastStore((s) => s.push);
  const addMeal = useAddPlanMeal(plan.id);
  const showMeals = plan.content_mode !== "targets_only";

  const foodIds = useMemo(() => {
    const set = new Set<string>();
    for (const meal of day.meals) for (const item of meal.items) set.add(item.food_id);
    return [...set].sort();
  }, [day.meals]);

  const foodNames = useQuery({
    queryKey: ["plan-food-names", foodIds.join(",")],
    queryFn: async () => {
      const out: FoodNames = new Map();
      await Promise.all(
        foodIds.map(async (id) => {
          try {
            const food: FoodResponse = await getFood(id);
            out.set(id, food.name);
          } catch {
            // Row falls back to "Food".
          }
        }),
      );
      return out;
    },
    enabled: foodIds.length > 0,
    staleTime: 5 * 60_000,
  });
  const names: FoodNames = foodNames.data ?? new Map();

  const dayLine = trackingLine(day.totals, plan.tracking_mode);

  return (
    <div className="flex flex-col gap-4">
      <div className="text-text-tertiary flex items-center justify-between text-xs tabular-nums">
        <span className="font-semibold tracking-[0.08em] uppercase">
          {dayRoleLabel(day.day_role)} · day total
        </span>
        <span>{dayLine}</span>
      </div>

      {showMeals ? (
        <>
          <div className="flex flex-col gap-3">
            {day.meals.map((meal) => (
              <MealCard key={meal.id} plan={plan} meal={meal} foodNames={names} />
            ))}
            {day.meals.length === 0 ? (
              <p className="text-text-tertiary border-border-strong rounded-[var(--radius-card)] border border-dashed py-6 text-center text-sm">
                No meals yet. Add one to start planning.
              </p>
            ) : null}
          </div>

          <button
            type="button"
            disabled={addMeal.isPending}
            onClick={() =>
              addMeal.mutate(
                {
                  dayId: day.id,
                  body: { name: `Meal ${day.meals.length + 1}`, slot_index: day.meals.length },
                },
                {
                  onError: () => pushToast({ kind: "error", message: "Could not add meal." }),
                },
              )
            }
            className="border-border-strong text-text-secondary hover:text-text flex w-full items-center justify-center gap-1.5 rounded-[var(--radius-button)] border border-dashed py-2.5 text-sm font-medium disabled:opacity-50"
          >
            <Plus className="h-4 w-4" aria-hidden /> Add meal
          </button>
        </>
      ) : (
        <p className="text-text-tertiary text-sm">
          This plan tracks targets only. Set the targets above; no meals are planned.
        </p>
      )}
    </div>
  );
}

function MealCard({
  plan,
  meal,
  foodNames,
}: {
  plan: MealPlan;
  meal: MealPlanMeal;
  foodNames: FoodNames;
}) {
  const pushToast = useToastStore((s) => s.push);
  const updateMeal = useUpdatePlanMeal(plan.id);
  const deleteMeal = useDeletePlanMeal(plan.id);
  const addItem = useAddPlanItem(plan.id);

  const [name, setName] = useState(meal.name);
  const [time, setTime] = useState(meal.planned_time ?? "");
  const [pickerOpen, setPickerOpen] = useState(false);

  const saveName = () => {
    const next = name.trim() || meal.name;
    if (next !== meal.name) updateMeal.mutate({ mealId: meal.id, body: { name: next } });
  };

  const saveTime = (value: string) => {
    setTime(value);
    updateMeal.mutate({ mealId: meal.id, body: { planned_time: value || null } });
  };

  const onPick = (picked: PickedIngredient) => {
    addItem.mutate(
      {
        mealId: meal.id,
        body: {
          food_id: picked.food.id,
          amount: picked.amount,
          unit: picked.unit,
          serving_id: picked.serving?.id ?? null,
        },
      },
      {
        onError: () => pushToast({ kind: "error", message: "Could not add food." }),
      },
    );
    setPickerOpen(false);
  };

  return (
    <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-3">
      <div className="flex items-center gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={saveName}
          className="text-text min-w-0 flex-1 bg-transparent text-sm font-semibold outline-none"
          aria-label="Meal name"
        />
        <span className="text-text-tertiary text-[11px] tabular-nums">
          {trackingLine(meal.totals, plan.tracking_mode)}
        </span>
        <button
          type="button"
          aria-label="Remove meal"
          onClick={() => deleteMeal.mutate(meal.id)}
          className="text-text-tertiary hover:text-destructive p-1"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>

      {/* Optional planned time */}
      <label className="text-text-tertiary mt-1 flex w-fit items-center gap-1.5 text-xs">
        <Clock className="h-3.5 w-3.5" aria-hidden />
        <input
          type="time"
          value={time}
          onChange={(e) => saveTime(e.target.value)}
          className="bg-transparent text-xs outline-none"
          aria-label="Planned time (optional)"
        />
      </label>

      {/* Items */}
      {meal.items.length > 0 ? (
        <div className="mt-2 flex flex-col gap-1.5">
          {meal.items.map((item) => (
            <ItemRow
              key={item.id}
              planId={plan.id}
              item={item}
              name={foodNames.get(item.food_id) ?? "Food"}
            />
          ))}
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setPickerOpen(true)}
        className="text-accent mt-2 text-xs font-semibold"
      >
        + Add food
      </button>

      <IngredientPicker
        open={pickerOpen}
        title={`Add to ${meal.name}`}
        onClose={() => setPickerOpen(false)}
        onPick={onPick}
      />
    </div>
  );
}

function ItemRow({ planId, item, name }: { planId: string; item: MealPlanItem; name: string }) {
  const deleteItem = useDeletePlanItem(planId);
  const grams = Math.round(num(item.grams));
  return (
    <div className="text-text flex items-center gap-2 text-sm">
      <span className="min-w-0 flex-1 truncate">{name}</span>
      <span className="text-text-tertiary text-xs tabular-nums">
        {Math.round(num(item.amount))} {item.unit === "serving" ? "×" : item.unit} · {grams} g ·{" "}
        {Math.round(num(item.kcal))} kcal
      </span>
      <button
        type="button"
        aria-label="Remove food"
        onClick={() => deleteItem.mutate(item.id)}
        className="text-text-tertiary hover:text-destructive"
      >
        <X className="h-3.5 w-3.5" aria-hidden />
      </button>
    </div>
  );
}
