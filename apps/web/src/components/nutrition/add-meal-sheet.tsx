"use client";

import {
  IngredientPicker,
  type PickedIngredient,
} from "@/components/nutrition/ingredient-picker";
import type { FoodResponse, MealType } from "@/lib/api/nutrition";

interface Props {
  open: boolean;
  mealType: MealType | null;
  onClose: () => void;
  onPick: (food: FoodResponse, grams: number) => void;
}

const TYPE_LABEL: Record<MealType, string> = {
  breakfast: "breakfast",
  lunch: "lunch",
  dinner: "dinner",
  snack: "snack",
};

/**
 * Thin wrapper over the shared {@link IngredientPicker} that flattens a picked
 * ingredient down to (food, grams) for the day's meal logging flow.
 */
export function AddMealSheet({ open, mealType, onClose, onPick }: Props) {
  const title = mealType ? `Add to ${TYPE_LABEL[mealType]}` : "Add food";

  return (
    <IngredientPicker
      open={open}
      title={title}
      onClose={onClose}
      onPick={(picked: PickedIngredient) => {
        onPick(picked.food, picked.grams);
        onClose();
      }}
    />
  );
}
