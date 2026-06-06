"use client";

import { Search } from "lucide-react";
import { useState } from "react";

import { BarcodeScanner } from "@/components/nutrition/barcode-scanner";
import { Sheet } from "@/components/ui/sheet";
import { UnderlineTabs } from "@/components/ui/tabs";
import type { FoodResponse, MealType } from "@/lib/api/nutrition";
import { useFoodSearch } from "@/lib/hooks/nutrition";

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

type Tab = "search" | "scan";

const TABS = [
  { value: "search" as const, label: "Search" },
  { value: "scan" as const, label: "Scan" },
];

function n(value: string | null | undefined): number {
  if (value == null) return 0;
  const x = Number(value);
  return Number.isFinite(x) ? x : 0;
}

export function AddMealSheet({ open, mealType, onClose, onPick }: Props) {
  const [tab, setTab] = useState<Tab>("search");
  const [query, setQuery] = useState("");
  const search = useFoodSearch(query, open && tab === "search");

  const title = mealType ? `Add to ${TYPE_LABEL[mealType]}` : "Add food";

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title={title}>
      <div className="flex flex-col gap-3">
        <UnderlineTabs tabs={TABS} value={tab} onChange={setTab} ariaLabel="Add food method" />

        {tab === "search" ? (
          <div className="flex flex-col gap-3">
            <div className="bg-surface border-border flex items-center gap-2 rounded-[10px] border px-3 py-2">
              <Search className="text-text-tertiary h-4 w-4 shrink-0" />
              <input
                type="search"
                placeholder="Search foods, brands…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
                className="text-text placeholder:text-text-tertiary w-full bg-transparent text-sm outline-none"
              />
            </div>

            <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
              {query.trim().length >= 2 ? "Results" : "Type at least 2 characters"}
            </span>

            <div className="flex max-h-[60vh] flex-col overflow-y-auto">
              {search.isLoading ? (
                <p className="text-text-secondary px-2 py-3 text-sm">Searching…</p>
              ) : search.isError ? (
                <p className="text-destructive px-2 py-3 text-sm">Search failed. Try again.</p>
              ) : search.data && search.data.items.length === 0 && query.trim().length >= 2 ? (
                <p className="text-text-tertiary px-2 py-6 text-center text-sm">
                  No matches for &quot;{query}&quot;.
                </p>
              ) : (
                search.data?.items.map((food) => (
                  <FoodRow
                    key={food.id}
                    food={food}
                    onPick={() => onPick(food, n(food.serving_size_g) || 100)}
                  />
                ))
              )}
            </div>
          </div>
        ) : null}

        {tab === "scan" ? (
          <BarcodeScanner onFound={(food) => onPick(food, n(food.serving_size_g) || 100)} />
        ) : null}
      </div>
    </Sheet>
  );
}

interface FoodRowProps {
  food: FoodResponse;
  onPick: () => void;
}

function FoodRow({ food, onPick }: FoodRowProps) {
  const kcal = Math.round(n(food.kcal_per_100g));
  const p = Math.round(n(food.protein_g_per_100g));
  const c = Math.round(n(food.carbs_g_per_100g));
  const f = Math.round(n(food.fat_g_per_100g));
  return (
    <button
      type="button"
      onClick={onPick}
      className="border-border hover:bg-surface grid grid-cols-[1fr_auto] gap-3 border-b px-2 py-3 text-left transition-colors duration-150 ease-out last:border-b-0"
    >
      <div className="min-w-0">
        <div className="text-text truncate text-sm font-medium">{food.name}</div>
        <div className="text-text-tertiary mt-0.5 text-[11px]">
          {food.brand ?? food.source} · per 100 g
        </div>
      </div>
      <div className="text-right">
        <div className="text-text font-serif text-[13px] font-semibold tabular-nums">
          {kcal} kcal
        </div>
        <div className="text-text-tertiary text-[11px] tabular-nums">
          {p}p · {c}c · {f}f
        </div>
      </div>
    </button>
  );
}
