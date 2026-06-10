"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { num } from "@/lib/api/meal-plans";
import type {
  FoodResponse,
  MealItemResponse,
  MealItemUnit,
  MealItemUpdate,
  MealResponse,
} from "@/lib/api/nutrition";
import { macroSummary, macrosForGrams, resolveGrams } from "@/lib/nutrition/macros";

interface Props {
  open: boolean;
  onClose: () => void;
  meal: MealResponse | null;
  foodLookup: Map<string, FoodResponse>;
  /** Persist one item's new amount/unit/serving. */
  onSaveItem: (itemId: string, body: MealItemUpdate) => Promise<void> | void;
  pending?: boolean;
}

const GRAM_UNIT = "__g__";
const ML_UNIT = "__ml__";

/** Adjust serving sizes of a completed/logged meal item by item. */
export function EditMealSheet({ open, onClose, meal, foodLookup, onSaveItem, pending }: Props) {
  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title="Edit meal">
      <div className="flex flex-col gap-3">
        {meal && meal.items.length > 0 ? (
          meal.items.map((item) => (
            <EditItemRow
              key={item.id}
              item={item}
              food={foodLookup.get(item.food_id)}
              onSave={(body) => onSaveItem(item.id, body)}
              pending={pending}
            />
          ))
        ) : (
          <p className="text-text-tertiary py-4 text-center text-[13px]">No items to edit.</p>
        )}
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </Sheet>
  );
}

function initialUnitToken(item: MealItemResponse): string {
  if (item.serving_id) return item.serving_id;
  if (item.unit === "ml") return ML_UNIT;
  return GRAM_UNIT;
}

function initialAmount(item: MealItemResponse): string {
  const amount = num(item.amount);
  if (amount > 0) return String(amount);
  return String(Math.round(num(item.grams)));
}

function EditItemRow({
  item,
  food,
  onSave,
  pending,
}: {
  item: MealItemResponse;
  food: FoodResponse | undefined;
  onSave: (body: MealItemUpdate) => Promise<void> | void;
  pending?: boolean;
}) {
  const servings = food?.servings ?? [];
  const [amountStr, setAmountStr] = useState(() => initialAmount(item));
  const [unitToken, setUnitToken] = useState(() => initialUnitToken(item));

  // Re-sync when the underlying item changes (after a save invalidates the query).
  useEffect(() => {
    setAmountStr(initialAmount(item));
    setUnitToken(initialUnitToken(item));
  }, [item]);

  const amount = num(amountStr);
  const serving =
    unitToken === GRAM_UNIT || unitToken === ML_UNIT
      ? null
      : (servings.find((s) => s.id === unitToken) ?? null);
  const unit: MealItemUnit = unitToken === ML_UNIT ? "ml" : serving ? "serving" : "g";

  const grams = food ? resolveGrams(food, amount, unit, serving) : amount;
  const macros = food ? macrosForGrams(food, grams) : null;

  const dirty = amountStr !== initialAmount(item) || unitToken !== initialUnitToken(item);

  const save = () => {
    onSave({ amount, unit, serving_id: unit === "serving" ? (serving?.id ?? null) : null });
  };

  return (
    <div className="border-border bg-surface rounded-[var(--radius-card)] border p-3">
      <div className="text-text mb-2 text-sm font-medium">{food?.name ?? "Food"}</div>
      <div className="grid grid-cols-[1fr_1.4fr] gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
            Amount
          </span>
          <Input
            type="number"
            inputMode="decimal"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            className="h-9 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
            Unit
          </span>
          <select
            value={unitToken}
            onChange={(e) => setUnitToken(e.target.value)}
            className="border-border-strong bg-surface-elevated text-text h-9 w-full rounded-[var(--radius-button)] border px-2 text-sm"
            aria-label="Unit"
          >
            <option value={GRAM_UNIT}>grams (g)</option>
            <option value={ML_UNIT}>millilitres (ml)</option>
            {servings.map((s) => (
              <option key={s.id} value={s.id}>
                {s.description}
                {num(s.grams) ? ` (${Math.round(num(s.grams))} g)` : ""}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <span className="text-text-secondary text-[11px] tabular-nums">
          ≈ {Math.round(grams)} g{macros ? ` · ${macroSummary(macros)}` : ""}
        </span>
        <Button
          size="sm"
          variant="secondary"
          disabled={!dirty || amount <= 0 || pending}
          onClick={save}
        >
          {pending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden /> : null}
          Save
        </Button>
      </div>
    </div>
  );
}
