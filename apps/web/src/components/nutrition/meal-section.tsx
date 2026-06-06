"use client";

import { X } from "lucide-react";

import { cn } from "@/lib/cn";
import type { MealItemResponse, MealResponse, MealType } from "@/lib/api/nutrition";
import type { FoodResponse } from "@/lib/api/nutrition";

interface Props {
  meal: MealResponse | null;
  type: MealType;
  foodLookup: Map<string, FoodResponse>;
  onAdd: (type: MealType) => void;
  onDelete: (itemId: string) => void;
}

const TYPE_LABEL: Record<MealType, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
};

function n(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

function totalsFor(items: MealItemResponse[]) {
  return items.reduce(
    (acc, item) => ({
      kcal: acc.kcal + n(item.kcal),
      p: acc.p + n(item.protein_g),
      c: acc.c + n(item.carbs_g),
      f: acc.f + n(item.fat_g),
    }),
    { kcal: 0, p: 0, c: 0, f: 0 },
  );
}

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export function MealSection({ meal, type, foodLookup, onAdd, onDelete }: Props) {
  const label = TYPE_LABEL[type];
  const items = meal?.items ?? [];
  const totals = totalsFor(items);

  return (
    <section className="mt-6">
      <div className="mb-2.5 flex items-baseline justify-between gap-2 px-1">
        <h3 className="text-text flex items-center gap-2.5 text-sm font-semibold">
          {label}
          {meal ? (
            <span className="text-text-tertiary text-[11px] font-medium">
              {timeLabel(meal.eaten_at)}
            </span>
          ) : null}
        </h3>
        {items.length > 0 ? (
          <span className="text-text-secondary font-serif text-[12px] font-medium tabular-nums">
            {Math.round(totals.kcal)} kcal · {Math.round(totals.p)}p · {Math.round(totals.c)}c ·{" "}
            {Math.round(totals.f)}f
          </span>
        ) : null}
      </div>
      <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border">
        {items.length === 0 ? (
          <p className="text-text-tertiary px-4 py-6 text-center text-[13px]">
            No items. Tap + to log {label.toLowerCase()}.
          </p>
        ) : (
          items.map((item) => (
            <MealItemRow
              key={item.id}
              item={item}
              food={foodLookup.get(item.food_id)}
              onDelete={() => onDelete(item.id)}
            />
          ))
        )}
        <div className={cn("px-3 pb-3", items.length === 0 ? "pt-0" : "pt-2.5")}>
          <button
            type="button"
            onClick={() => onAdd(type)}
            className="border-border-strong text-text-tertiary hover:border-accent hover:text-accent hover:bg-accent-soft flex w-full items-center justify-center gap-2 rounded-[10px] border border-dashed py-3 text-[13px] font-medium transition-colors duration-150 ease-out"
          >
            + Add to {label.toLowerCase()}
          </button>
        </div>
      </div>
    </section>
  );
}

interface RowProps {
  item: MealItemResponse;
  food: FoodResponse | undefined;
  onDelete: () => void;
}

function MealItemRow({ item, food, onDelete }: RowProps) {
  const name = food?.name ?? "Food";
  const brand = food?.brand;
  const grams = Math.round(n(item.grams));

  return (
    <div className="border-border grid grid-cols-[1fr_3.5rem_3.5rem_5rem_1.5rem] items-center gap-3 border-b px-4 py-3 text-[13px] last:border-b-0">
      <div className="min-w-0">
        <div className="text-text truncate font-medium">{name}</div>
        {brand ? <div className="text-text-tertiary mt-0.5 text-[11px]">{brand}</div> : null}
      </div>
      <span className="text-text-secondary text-right font-serif tabular-nums">{grams}g</span>
      <span className="text-text text-right font-serif font-semibold tabular-nums">
        {Math.round(n(item.kcal))}
      </span>
      <span className="text-text-secondary text-right text-[11px] tabular-nums">
        <span className="text-accent font-serif font-semibold">
          {Math.round(n(item.protein_g))}p
        </span>{" "}
        · {Math.round(n(item.carbs_g))}c · {Math.round(n(item.fat_g))}f
      </span>
      <button
        type="button"
        onClick={onDelete}
        aria-label="Delete item"
        className="text-text-tertiary hover:text-destructive flex h-7 w-7 items-center justify-center"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
