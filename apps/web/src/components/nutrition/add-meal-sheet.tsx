"use client";

import { IngredientPicker, type PickedIngredient } from "@/components/nutrition/ingredient-picker";

interface Props {
  open: boolean;
  /** The meal the picked food is logged into, for the "Add to {name}" title. */
  mealName: string;
  /** Which tab to open on — "scan" for the Scan affordance. */
  initialTab?: "search" | "scan";
  onClose: () => void;
  /** Called with each picked food; adds it to the target meal and dismisses. */
  onPick: (picked: PickedIngredient) => void;
}

/**
 * Add-meal flow for the Direction A day screen. Reuses the existing
 * search/scan/manual {@link IngredientPicker} (lazy-loaded by the caller) but
 * routes the result into a specific target meal — a plan slot, an existing
 * flexible meal, or a freshly created one. Photo recognition was removed, so
 * there is no Photo tab.
 */
export function AddMealSheet({ open, mealName, initialTab = "search", onClose, onPick }: Props) {
  return (
    <IngredientPicker
      open={open}
      title={`Add to ${mealName}`}
      initialTab={initialTab}
      onClose={onClose}
      onPick={onPick}
    />
  );
}
