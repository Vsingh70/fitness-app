"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { Check, Trash2, X } from "lucide-react";
import { memo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { num } from "@/lib/api/meal-plans";
import type { FoodResponse, MealItemResponse, MealItemUpdate, Serving } from "@/lib/api/nutrition";
import { macroSummary, macrosForGrams, resolveGrams } from "@/lib/nutrition/macros";

/** One row in the day's meal list: a plan slot or a flexible meal. */
export interface MealRowModel {
  /** Stable key (logged meal id, or `slot:{planMealId}` for an empty slot). */
  key: string;
  name: string;
  /** Logged meal id, or null for an empty/unlogged plan slot. */
  mealId: string | null;
  /** Set when the meal is backed by a plan slot (enables "forever" delete). */
  sourcePlanMealId: string | null;
  /** ISO eaten-at, or null for an empty/unlogged slot. */
  eatenAt: string | null;
  items: MealItemResponse[];
  /** Open the add-meal flow into this row's meal. */
  onAddFood: () => void;
}

interface Props {
  rows: MealRowModel[];
  foodLookup: Map<string, FoodResponse>;
  onDeleteItem: (itemId: string) => void;
  /** Commit an amount/unit/serving edit for a logged item. */
  onEditItem: (itemId: string, body: MealItemUpdate) => void;
  /** Delete a whole logged meal; "forever" also drops a plan-backed template. */
  onDeleteMeal: (mealId: string, scope: "today" | "forever") => void;
}

function n(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

function timeLabel(iso: string): string {
  return new Date(iso)
    .toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    .toUpperCase();
}

function totalsFor(items: MealItemResponse[]) {
  return items.reduce(
    (acc, item) => ({ kcal: acc.kcal + n(item.kcal), p: acc.p + n(item.protein_g) }),
    { kcal: 0, p: 0 },
  );
}

export function MealList({ rows, foodLookup, onDeleteItem, onEditItem, onDeleteMeal }: Props) {
  // Window the rows: a day can hold an unbounded number of meals, so only the
  // visible MealRows mount. Short days sit under max-height and never scroll.
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 132,
    overscan: 6,
  });

  return (
    <div ref={parentRef} className="max-h-[70vh] overflow-y-auto">
      <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const row = rows[virtualRow.index];
          if (!row) return null;
          return (
            <div
              key={row.key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <MealRow
                row={row}
                foodLookup={foodLookup}
                onDeleteItem={onDeleteItem}
                onEditItem={onEditItem}
                onDeleteMeal={onDeleteMeal}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const MealRow = memo(function MealRow({
  row,
  foodLookup,
  onDeleteItem,
  onEditItem,
  onDeleteMeal,
}: {
  row: MealRowModel;
  foodLookup: Map<string, FoodResponse>;
  onDeleteItem: (itemId: string) => void;
  onEditItem: (itemId: string, body: MealItemUpdate) => void;
  onDeleteMeal: (mealId: string, scope: "today" | "forever") => void;
}) {
  const totals = totalsFor(row.items);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  return (
    <section className="border-border grid grid-cols-[96px_1fr_auto] gap-4 border-t py-5 first:border-t-0">
      {/* When column */}
      <div className="flex flex-col">
        <span className="text-text font-serif text-[16px] font-medium">{row.name}</span>
        {row.eatenAt ? (
          <span className="text-text-tertiary mt-0.5 text-[10px] font-semibold tracking-[0.08em] uppercase">
            {timeLabel(row.eatenAt)}
          </span>
        ) : null}
        {row.mealId ? (
          <MealDelete
            confirming={confirmingDelete}
            onOpen={() => setConfirmingDelete(true)}
            onCancel={() => setConfirmingDelete(false)}
            isPlanBacked={row.sourcePlanMealId !== null}
            onDelete={(scope) => {
              setConfirmingDelete(false);
              onDeleteMeal(row.mealId!, scope);
            }}
          />
        ) : null}
      </div>

      {/* Entry lines */}
      <div className="min-w-0">
        {row.items.length === 0 ? (
          <button
            type="button"
            onClick={row.onAddFood}
            className="text-text-tertiary hover:text-accent text-[13px]"
          >
            + Add food
          </button>
        ) : (
          <div className="flex flex-col gap-2">
            {row.items.map((item) => {
              const food = foodLookup.get(item.food_id);
              if (editingId === item.id) {
                return (
                  <ItemEditor
                    key={item.id}
                    item={item}
                    food={food}
                    onCancel={() => setEditingId(null)}
                    onSave={(body) => {
                      setEditingId(null);
                      onEditItem(item.id, body);
                    }}
                  />
                );
              }
              return (
                <div
                  key={item.id}
                  className="grid grid-cols-[1fr_auto_1.25rem] items-baseline gap-3 text-[13px]"
                >
                  <button
                    type="button"
                    onClick={() => setEditingId(item.id)}
                    className="text-text hover:text-accent min-w-0 truncate text-left"
                  >
                    {food?.name ?? "Food"}{" "}
                    <span className="text-text-tertiary tabular-nums">
                      · {Math.round(n(item.grams))} g
                    </span>
                  </button>
                  <span className="text-text-secondary text-right font-serif tabular-nums">
                    {Math.round(n(item.kcal))}
                  </span>
                  <button
                    type="button"
                    onClick={() => onDeleteItem(item.id)}
                    aria-label="Delete item"
                    className="text-text-tertiary hover:text-destructive flex h-5 w-5 items-center justify-center"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </div>
              );
            })}
            <button
              type="button"
              onClick={row.onAddFood}
              className="text-text-tertiary hover:text-accent mt-0.5 self-start text-[12px]"
            >
              + Add food
            </button>
          </div>
        )}
      </div>

      {/* Kcal total */}
      <div className="flex flex-col items-end">
        <span className="text-text font-serif text-[20px] font-medium tabular-nums">
          {Math.round(totals.kcal)}
        </span>
        {totals.p > 0 ? (
          <span className="text-accent text-[11px] font-medium tabular-nums">
            {Math.round(totals.p)}g protein
          </span>
        ) : null}
      </div>
    </section>
  );
});

// Per-meal delete -----------------------------------------------------------
function MealDelete({
  confirming,
  isPlanBacked,
  onOpen,
  onCancel,
  onDelete,
}: {
  confirming: boolean;
  isPlanBacked: boolean;
  onOpen: () => void;
  onCancel: () => void;
  onDelete: (scope: "today" | "forever") => void;
}) {
  if (!confirming) {
    return (
      <button
        type="button"
        onClick={onOpen}
        aria-label="Delete meal"
        className="text-text-tertiary hover:text-destructive mt-2 flex w-fit items-center gap-1 text-[11px]"
      >
        <Trash2 className="h-3 w-3" aria-hidden /> Delete
      </button>
    );
  }
  return (
    <div className="mt-2 flex flex-col gap-1.5">
      {isPlanBacked ? (
        <>
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
            Delete this meal
          </span>
          <button
            type="button"
            onClick={() => onDelete("today")}
            className="text-text hover:text-accent text-left text-[12px]"
          >
            Just today
          </button>
          <button
            type="button"
            onClick={() => onDelete("forever")}
            className="text-text hover:text-destructive text-left text-[12px]"
          >
            From the plan
          </button>
        </>
      ) : (
        <button
          type="button"
          onClick={() => onDelete("today")}
          className="text-destructive text-left text-[12px]"
        >
          Confirm delete
        </button>
      )}
      <button
        type="button"
        onClick={onCancel}
        className="text-text-tertiary hover:text-text text-left text-[11px]"
      >
        Cancel
      </button>
    </div>
  );
}

// Inline amount/unit editor (mirrors the picker's amount step) --------------
const GRAM_UNIT = "__g__";
const ML_UNIT = "__ml__";

function ItemEditor({
  item,
  food,
  onCancel,
  onSave,
}: {
  item: MealItemResponse;
  food: FoodResponse | undefined;
  onCancel: () => void;
  onSave: (body: MealItemUpdate) => void;
}) {
  const servings: Serving[] = food?.servings ?? [];
  const [amountStr, setAmountStr] = useState(() =>
    item.amount != null ? String(num(item.amount)) : String(Math.round(num(item.grams))),
  );
  const [unitToken, setUnitToken] = useState<string>(() => {
    if (item.unit === "serving" && item.serving_id) return item.serving_id;
    if (item.unit === "ml") return ML_UNIT;
    return GRAM_UNIT;
  });

  const amount = num(amountStr);
  const serving =
    unitToken === GRAM_UNIT || unitToken === ML_UNIT
      ? null
      : (servings.find((s) => s.id === unitToken) ?? null);
  const unit: "g" | "ml" | "serving" = unitToken === ML_UNIT ? "ml" : serving ? "serving" : "g";

  // Preview only — the server is the source of truth for grams/macros on save.
  const grams = food ? resolveGrams(food, amount, unit, serving) : amount;
  const macros = food ? macrosForGrams(food, grams) : null;

  const save = () =>
    onSave({
      amount,
      unit,
      serving_id: unit === "serving" ? (serving?.id ?? null) : null,
    });

  return (
    <div className="border-border bg-surface flex flex-col gap-3 rounded-[var(--radius-card)] border p-3">
      <div className="grid grid-cols-[1fr_1.4fr] gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
            Amount
          </span>
          <Input
            type="number"
            inputMode="decimal"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            className="h-9 text-sm"
            autoFocus
          />
        </label>
        <label className="flex flex-col gap-1">
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

      <div className="text-text-secondary flex items-center justify-between text-[12px] tabular-nums">
        <span>≈ {Math.round(grams)} g</span>
        {macros ? <span>{macroSummary(macros)}</span> : null}
      </div>

      <div className="flex items-center justify-end gap-2">
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button size="sm" disabled={amount <= 0} onClick={save}>
          <Check className="mr-1.5 h-4 w-4" aria-hidden /> Save
        </Button>
      </div>
    </div>
  );
}
