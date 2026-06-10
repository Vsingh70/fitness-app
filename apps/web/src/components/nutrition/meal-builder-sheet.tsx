"use client";

import { Loader2, Plus, X } from "lucide-react";
import { useMemo, useState } from "react";

import { IngredientPicker, type PickedIngredient } from "@/components/nutrition/ingredient-picker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { UnderlineTabs } from "@/components/ui/tabs";
import type { MealType } from "@/lib/api/nutrition";
import { type Macros, macroSummary, macrosForGrams } from "@/lib/nutrition/macros";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Save the built meal. `eatenAt` is an ISO string when the user set a time. */
  onSave: (input: {
    mealType: MealType;
    eatenAt: string | null;
    ingredients: PickedIngredient[];
  }) => Promise<void> | void;
  saving?: boolean;
  /**
   * When set, the builder runs in "swap" mode: meal type/time are fixed and the
   * primary action label changes. Used by the swap flow to build fresh items.
   */
  swapMode?: boolean;
  title?: string;
}

const MEAL_TYPE_TABS: { value: MealType; label: string }[] = [
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "dinner", label: "Dinner" },
  { value: "snack", label: "Snack" },
];

function totalsFor(ingredients: PickedIngredient[]): Macros {
  return ingredients.reduce<Macros>(
    (acc, ing) => {
      const m = macrosForGrams(ing.food, ing.grams);
      return {
        kcal: acc.kcal + m.kcal,
        protein_g: acc.protein_g + m.protein_g,
        carbs_g: acc.carbs_g + m.carbs_g,
        fat_g: acc.fat_g + m.fat_g,
      };
    },
    { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 },
  );
}

/**
 * Multi-ingredient meal builder. Reuses the shared {@link IngredientPicker} to add
 * foods (search/scan/manual) each with their own amount + unit, shows running
 * totals, and hands the full list back for saving.
 */
export function MealBuilderSheet({
  open,
  onClose,
  onSave,
  saving = false,
  swapMode = false,
  title,
}: Props) {
  const [mealType, setMealType] = useState<MealType>("breakfast");
  const [timeStr, setTimeStr] = useState("");
  const [ingredients, setIngredients] = useState<PickedIngredient[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);

  const totals = useMemo(() => totalsFor(ingredients), [ingredients]);

  const reset = () => {
    setMealType("breakfast");
    setTimeStr("");
    setIngredients([]);
    setPickerOpen(false);
  };

  const close = () => {
    reset();
    onClose();
  };

  const save = async () => {
    if (ingredients.length === 0) return;
    let eatenAt: string | null = null;
    if (timeStr) {
      const [h, min] = timeStr.split(":").map((s) => Number.parseInt(s, 10));
      const d = new Date();
      d.setHours(h ?? 0, min ?? 0, 0, 0);
      eatenAt = d.toISOString();
    }
    await onSave({ mealType, eatenAt, ingredients });
    reset();
  };

  const heading = title ?? (swapMode ? "Build a new meal" : "Track a meal");

  return (
    <>
      <Sheet open={open} onOpenChange={(v) => (v ? null : close())} title={heading}>
        <div className="flex flex-col gap-4">
          {!swapMode ? (
            <div className="flex flex-col gap-2">
              <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
                Meal
              </span>
              <UnderlineTabs
                tabs={MEAL_TYPE_TABS}
                value={mealType}
                onChange={setMealType}
                ariaLabel="Meal type"
              />
            </div>
          ) : null}

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
                Ingredients
              </span>
              <span className="text-text-secondary font-serif text-[12px] font-medium tabular-nums">
                {ingredients.length > 0 ? macroSummary(totals) : "Nothing yet"}
              </span>
            </div>

            <div className="border-border bg-surface rounded-[var(--radius-card)] border">
              {ingredients.length === 0 ? (
                <p className="text-text-tertiary px-4 py-6 text-center text-[13px]">
                  Add foods by search, scan, or manual entry.
                </p>
              ) : (
                ingredients.map((ing, idx) => (
                  <IngredientRow
                    key={`${ing.food.id}-${idx}`}
                    ingredient={ing}
                    onRemove={() => setIngredients((prev) => prev.filter((_, i) => i !== idx))}
                  />
                ))
              )}
            </div>

            <button
              type="button"
              onClick={() => setPickerOpen(true)}
              className="border-border-strong text-text-tertiary hover:border-accent hover:text-accent hover:bg-accent-soft flex w-full items-center justify-center gap-2 rounded-[10px] border border-dashed py-3 text-[13px] font-medium transition-colors duration-150 ease-out"
            >
              <Plus className="h-4 w-4" aria-hidden /> Add ingredient
            </button>
          </div>

          {!swapMode ? (
            <label className="flex flex-col gap-1.5">
              <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
                Time eaten (optional)
              </span>
              <Input
                type="time"
                value={timeStr}
                onChange={(e) => setTimeStr(e.target.value)}
                className="w-[140px]"
              />
            </label>
          ) : null}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={close}>
              Cancel
            </Button>
            <Button size="sm" disabled={ingredients.length === 0 || saving} onClick={save}>
              {saving ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden /> : null}
              {swapMode ? "Swap in" : "Save meal"}
            </Button>
          </div>
        </div>
      </Sheet>

      <IngredientPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onPick={(picked) => {
          setIngredients((prev) => [...prev, picked]);
          setPickerOpen(false);
        }}
      />
    </>
  );
}

function IngredientRow({
  ingredient,
  onRemove,
}: {
  ingredient: PickedIngredient;
  onRemove: () => void;
}) {
  const macros = macrosForGrams(ingredient.food, ingredient.grams);
  const unitLabel =
    ingredient.unit === "serving"
      ? (ingredient.serving?.description ?? "serving")
      : ingredient.unit;
  return (
    <div className="border-border grid grid-cols-[1fr_auto_1.5rem] items-center gap-3 border-b px-4 py-3 text-[13px] last:border-b-0">
      <div className="min-w-0">
        <div className="text-text truncate font-medium">{ingredient.food.name}</div>
        <div className="text-text-tertiary mt-0.5 text-[11px]">
          {ingredient.amount} {unitLabel} · {Math.round(ingredient.grams)} g
        </div>
      </div>
      <span className="text-text-secondary text-right text-[11px] tabular-nums">
        {macroSummary(macros)}
      </span>
      <button
        type="button"
        onClick={onRemove}
        aria-label="Remove ingredient"
        className="text-text-tertiary hover:text-destructive flex h-7 w-7 items-center justify-center"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
