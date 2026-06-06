"use client";

import { useState } from "react";
import { Search, Trash2, X } from "lucide-react";

import { Input } from "@/components/ui/input";
import { mealMacros, type PlannedItem, type PlannedMeal } from "@/lib/api/meal-plans";
import { useFoodSearch } from "@/lib/hooks/nutrition";

interface Props {
  meal: PlannedMeal;
  onChange: (meal: PlannedMeal) => void;
  onRemove: () => void;
}

function num(s: string): number {
  const x = Number(s);
  return Number.isFinite(x) && x >= 0 ? x : 0;
}

export function PlanMealEditor({ meal, onChange, onRemove }: Props) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const search = useFoodSearch(query, searchOpen && query.trim().length >= 2);

  const hasItems = meal.items.length > 0;
  const totals = mealMacros(meal);

  const addItem = (item: PlannedItem) => {
    onChange({ ...meal, items: [...meal.items, item] });
    setQuery("");
    setSearchOpen(false);
  };

  const removeItem = (idx: number) =>
    onChange({ ...meal, items: meal.items.filter((_, i) => i !== idx) });

  const setItemGrams = (idx: number, grams: number) =>
    onChange({
      ...meal,
      items: meal.items.map((it, i) => (i === idx ? { ...it, grams } : it)),
    });

  return (
    <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-3">
      {/* Meal label + remove */}
      <div className="flex items-center gap-2">
        <input
          value={meal.label}
          onChange={(e) => onChange({ ...meal, label: e.target.value })}
          className="text-text flex-1 bg-transparent text-sm font-semibold outline-none"
          aria-label="Meal name"
        />
        <span className="text-text-tertiary text-[11px] tabular-nums">
          {Math.round(totals.kcal)} kcal
        </span>
        <button
          type="button"
          aria-label="Remove meal"
          onClick={onRemove}
          className="text-text-tertiary hover:text-destructive p-1"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>

      {/* Linked food items */}
      {hasItems ? (
        <div className="mt-2 flex flex-col gap-1.5">
          {meal.items.map((it, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm">
              <span className="text-text min-w-0 flex-1 truncate">{it.name}</span>
              <Input
                type="number"
                inputMode="numeric"
                value={String(it.grams)}
                onChange={(e) => setItemGrams(idx, num(e.target.value))}
                className="h-8 w-20 text-sm"
                aria-label={`${it.name} grams`}
              />
              <span className="text-text-tertiary text-xs">g</span>
              <button
                type="button"
                aria-label="Remove item"
                onClick={() => removeItem(idx)}
                className="text-text-tertiary hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          ))}
        </div>
      ) : (
        /* Manual macros (only when no linked items) */
        <div className="mt-2 grid grid-cols-4 gap-2">
          <ManualField
            label="kcal"
            value={meal.kcal}
            onChange={(v) => onChange({ ...meal, kcal: v })}
          />
          <ManualField
            label="P"
            value={meal.protein_g}
            onChange={(v) => onChange({ ...meal, protein_g: v })}
          />
          <ManualField
            label="C"
            value={meal.carbs_g}
            onChange={(v) => onChange({ ...meal, carbs_g: v })}
          />
          <ManualField
            label="F"
            value={meal.fat_g}
            onChange={(v) => onChange({ ...meal, fat_g: v })}
          />
        </div>
      )}

      {/* Add-food affordance + search */}
      {!searchOpen ? (
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="text-accent mt-2 text-xs font-semibold"
        >
          + Add food from database
        </button>
      ) : (
        <div className="mt-2">
          <div className="bg-surface border-border flex items-center gap-2 rounded-[8px] border px-2.5 py-1.5">
            <Search className="text-text-tertiary h-4 w-4 shrink-0" aria-hidden />
            <input
              type="search"
              autoFocus
              placeholder="Search foods…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="text-text placeholder:text-text-tertiary w-full bg-transparent text-sm outline-none"
            />
            <button type="button" onClick={() => setSearchOpen(false)} aria-label="Close search">
              <X className="text-text-tertiary h-4 w-4" aria-hidden />
            </button>
          </div>
          <div className="mt-1 flex max-h-48 flex-col overflow-y-auto">
            {search.isLoading ? (
              <p className="text-text-secondary px-2 py-2 text-xs">Searching…</p>
            ) : search.data && search.data.items.length > 0 ? (
              search.data.items.map((food) => (
                <button
                  key={food.id}
                  type="button"
                  onClick={() =>
                    addItem({
                      food_id: food.id,
                      name: food.name,
                      grams: num(String(food.serving_size_g ?? "")) || 100,
                      kcal_per_100g: num(String(food.kcal_per_100g ?? "")),
                      protein_g_per_100g: num(String(food.protein_g_per_100g ?? "")),
                      carbs_g_per_100g: num(String(food.carbs_g_per_100g ?? "")),
                      fat_g_per_100g: num(String(food.fat_g_per_100g ?? "")),
                    })
                  }
                  className="hover:bg-surface border-border flex items-center justify-between gap-2 border-b px-2 py-2 text-left text-sm last:border-b-0"
                >
                  <span className="text-text min-w-0 truncate">{food.name}</span>
                  <span className="text-text-tertiary shrink-0 text-[11px] tabular-nums">
                    {Math.round(num(String(food.kcal_per_100g ?? "")))} kcal/100g
                  </span>
                </button>
              ))
            ) : query.trim().length >= 2 ? (
              <p className="text-text-tertiary px-2 py-2 text-xs">No matches.</p>
            ) : (
              <p className="text-text-tertiary px-2 py-2 text-xs">Type at least 2 characters.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ManualField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-text-tertiary text-[10px] font-semibold uppercase">{label}</span>
      <Input
        type="number"
        inputMode="numeric"
        value={String(value)}
        onChange={(e) => onChange(num(e.target.value))}
        className="h-8 text-sm"
      />
    </label>
  );
}
