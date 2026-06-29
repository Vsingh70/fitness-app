"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { Link2, Loader2, Plus, Search } from "lucide-react";
import { memo, useEffect, useRef, useState } from "react";

import { BarcodeScanner } from "@/components/nutrition/barcode-scanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { UnderlineTabs } from "@/components/ui/tabs";
import { useToastStore } from "@/components/ui/toast";
import { num } from "@/lib/api/meal-plans";
import {
  createFood,
  parseFoodUrl,
  type FoodResponse,
  type PickedIngredient,
} from "@/lib/api/nutrition";
import { useFoodSearch } from "@/lib/hooks/nutrition";
import { macroSummary, macrosForGrams, resolveGrams } from "@/lib/nutrition/macros";

export type { PickedIngredient };

interface Props {
  open: boolean;
  title?: string;
  /** Tab to open on; resets to it on close. Defaults to "search". */
  initialTab?: Tab;
  onClose: () => void;
  onPick: (picked: PickedIngredient) => void;
}

type Tab = "search" | "scan" | "manual";

const TABS = [
  { value: "search" as const, label: "Search" },
  { value: "scan" as const, label: "Scan barcode" },
  { value: "manual" as const, label: "Manual" },
];

export function IngredientPicker({
  open,
  title = "Add ingredient",
  initialTab = "search",
  onClose,
  onPick,
}: Props) {
  const [tab, setTab] = useState<Tab>(initialTab);
  // The food selected from search/scan, pending an amount + unit choice.
  const [selected, setSelected] = useState<FoodResponse | null>(null);

  const reset = () => {
    setSelected(null);
    setTab(initialTab);
  };

  // Land on the requested tab each time the picker opens (e.g. "Scan").
  useEffect(() => {
    if (open) {
      setTab(initialTab);
      setSelected(null);
    }
  }, [open, initialTab]);

  const close = () => {
    reset();
    onClose();
  };

  const commit = (picked: PickedIngredient) => {
    onPick(picked);
    reset();
  };

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : close())} title={title}>
      {selected ? (
        <AmountStep food={selected} onBack={() => setSelected(null)} onConfirm={commit} />
      ) : (
        <div className="flex flex-col gap-3">
          <UnderlineTabs
            tabs={TABS}
            value={tab}
            onChange={setTab}
            ariaLabel="Add ingredient method"
          />

          {tab === "search" ? <SearchTab onSelect={setSelected} /> : null}
          {tab === "scan" ? <BarcodeScanner onFound={setSelected} /> : null}
          {tab === "manual" ? <ManualTab onConfirm={commit} /> : null}
        </div>
      )}
    </Sheet>
  );
}

// Search ------------------------------------------------------------------
function SearchTab({ onSelect }: { onSelect: (food: FoodResponse) => void }) {
  const [query, setQuery] = useState("");
  const search = useFoodSearch(query, true);

  // Window the populated results: search can return an unbounded list, so only
  // the visible FoodRows mount.
  const parentRef = useRef<HTMLDivElement>(null);
  const items = search.data?.items ?? [];
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64,
    overscan: 6,
  });
  const hasResults =
    !search.isLoading &&
    !search.isError &&
    !(search.data && search.data.items.length === 0 && query.trim().length >= 2);

  return (
    <div className="flex flex-col gap-3">
      <div className="bg-surface border-border flex items-center gap-2 rounded-[10px] border px-3 py-2">
        <Search className="text-text-tertiary h-4 w-4 shrink-0" aria-hidden />
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

      <div ref={parentRef} className="flex max-h-[55vh] flex-col overflow-y-auto">
        {search.isLoading ? (
          <p className="text-text-secondary px-2 py-3 text-sm">Searching…</p>
        ) : search.isError ? (
          <p className="text-destructive px-2 py-3 text-sm">Search failed. Try again.</p>
        ) : search.data && search.data.items.length === 0 && query.trim().length >= 2 ? (
          <p className="text-text-tertiary px-2 py-6 text-center text-sm">
            No matches for &quot;{query}&quot;.
          </p>
        ) : hasResults ? (
          <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const food = items[virtualRow.index];
              if (!food) return null;
              return (
                <div
                  key={food.id}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <FoodRow food={food} onSelect={() => onSelect(food)} />
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export const FoodRow = memo(function FoodRow({
  food,
  onSelect,
}: {
  food: FoodResponse;
  onSelect: () => void;
}) {
  const kcal = Math.round(num(food.kcal_per_100g));
  const p = Math.round(num(food.protein_g_per_100g));
  const c = Math.round(num(food.carbs_g_per_100g));
  const f = Math.round(num(food.fat_g_per_100g));
  return (
    <button
      type="button"
      onClick={onSelect}
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
});

// Amount + unit step ------------------------------------------------------
const GRAM_UNIT = "__g__";
const ML_UNIT = "__ml__";

function AmountStep({
  food,
  onBack,
  onConfirm,
}: {
  food: FoodResponse;
  onBack: () => void;
  onConfirm: (picked: PickedIngredient) => void;
}) {
  const servings = food.servings ?? [];
  const defaultServing = servings.find((s) => s.is_default) ?? null;
  const [amountStr, setAmountStr] = useState(() =>
    defaultServing ? "1" : String(num(food.serving_size_g) || 100),
  );
  // The selected unit token: GRAM_UNIT, ML_UNIT, or a serving id.
  const [unitToken, setUnitToken] = useState<string>(() =>
    defaultServing ? defaultServing.id : GRAM_UNIT,
  );

  const amount = num(amountStr);
  const serving =
    unitToken === GRAM_UNIT || unitToken === ML_UNIT
      ? null
      : (servings.find((s) => s.id === unitToken) ?? null);
  const unit: "g" | "ml" | "serving" = unitToken === ML_UNIT ? "ml" : serving ? "serving" : "g";

  const grams = resolveGrams(food, amount, unit, serving);
  const macros = macrosForGrams(food, grams);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <button
          type="button"
          onClick={onBack}
          className="text-text-tertiary hover:text-text text-xs"
        >
          ← Pick a different food
        </button>
        <p className="text-text mt-2 text-base font-semibold">{food.name}</p>
        {food.brand ? <p className="text-text-tertiary text-xs">{food.brand}</p> : null}
      </div>

      <div className="grid grid-cols-[1fr_1.4fr] gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
            Amount
          </span>
          <Input
            type="number"
            inputMode="decimal"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            autoFocus
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
            Unit
          </span>
          <select
            value={unitToken}
            onChange={(e) => setUnitToken(e.target.value)}
            className="border-border-strong bg-surface-elevated text-text h-[42px] w-full rounded-[var(--radius-button)] border px-3 text-sm"
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

      <div className="border-border bg-surface rounded-[var(--radius-card)] border p-3 text-sm tabular-nums">
        <div className="text-text-secondary flex justify-between">
          <span>≈ {Math.round(grams)} g</span>
          <span>{macroSummary(macros)}</span>
        </div>
      </div>

      <div className="flex justify-end">
        <Button
          size="sm"
          disabled={amount <= 0}
          onClick={() => onConfirm({ food, amount, unit, serving, grams })}
        >
          <Plus className="mr-1.5 h-4 w-4" aria-hidden /> Add
        </Button>
      </div>
    </div>
  );
}

// Manual ------------------------------------------------------------------
function ManualTab({ onConfirm }: { onConfirm: (picked: PickedIngredient) => void }) {
  const pushToast = useToastStore((s) => s.push);
  const [name, setName] = useState("");
  const [amountStr, setAmountStr] = useState("100");
  const [kcal, setKcal] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [save, setSave] = useState(false);
  const [pending, setPending] = useState(false);
  const [url, setUrl] = useState("");
  const [importing, setImporting] = useState(false);

  const importFromUrl = async () => {
    if (!url.trim() || importing) return;
    setImporting(true);
    try {
      const parsed = await parseFoodUrl(url.trim());
      const s = (v: number | string | null | undefined) => (v == null ? "" : String(Number(v)));
      if (parsed.name) setName(parsed.brand ? `${parsed.brand} ${parsed.name}` : parsed.name);
      if (parsed.serving_grams != null) setAmountStr(s(parsed.serving_grams));
      setKcal(s(parsed.kcal));
      setProtein(s(parsed.protein_g));
      setCarbs(s(parsed.carbs_g));
      setFat(s(parsed.fat_g));
      pushToast({
        kind: parsed.warning ? "info" : "success",
        message: parsed.warning ?? "Nutrition imported — review and add.",
      });
    } catch (e) {
      const err = e as { status?: number; message?: string };
      pushToast({
        kind: "error",
        message:
          err?.status === 422
            ? "Couldn't find nutrition on that page."
            : (err?.message ?? "Couldn't import from that link."),
      });
    } finally {
      setImporting(false);
    }
  };

  const amount = num(amountStr);
  // Macros are entered for the chosen amount; store as per-100g on the food.
  const factor = amount > 0 ? 100 / amount : 0;

  const submit = async () => {
    if (!name.trim() || amount <= 0) return;
    const per100 = {
      kcal_per_100g: num(kcal) * factor,
      protein_g_per_100g: num(protein) * factor,
      carbs_g_per_100g: num(carbs) * factor,
      fat_g_per_100g: num(fat) * factor,
    };
    setPending(true);
    try {
      let food: FoodResponse;
      if (save) {
        food = await createFood({
          name: name.trim(),
          serving_size_g: amount,
          ...per100,
        });
      } else {
        // Ephemeral food shape for callers that hold macros client-side.
        food = {
          id: crypto.randomUUID(),
          name: name.trim(),
          brand: null,
          archived_at: null,
          carbs_g_per_100g: String(per100.carbs_g_per_100g),
          created_at: new Date().toISOString(),
          external_id: null,
          fat_g_per_100g: String(per100.fat_g_per_100g),
          fiber_g_per_100g: null,
          kcal_per_100g: String(per100.kcal_per_100g),
          owner_id: null,
          payload: {},
          protein_g_per_100g: String(per100.protein_g_per_100g),
          serving_label: null,
          serving_size_g: String(amount),
          servings: [],
          source: "user",
        };
      }
      onConfirm({ food, amount, unit: "g", serving: null, grams: amount });
    } catch {
      pushToast({ kind: "error", message: "Could not save food." });
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-1.5">
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
          Import from a link
        </span>
        <div className="flex gap-2">
          <Input
            type="url"
            inputMode="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void importFromUrl();
              }
            }}
            placeholder="Paste a recipe or product URL"
          />
          <Button
            size="sm"
            variant="secondary"
            disabled={!url.trim() || importing}
            onClick={importFromUrl}
          >
            {importing ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Link2 className="h-4 w-4" aria-hidden />
            )}
            <span className="ml-1.5">Fetch</span>
          </Button>
        </div>
        <span className="text-text-tertiary text-[11px]">
          Reads nutrition from the page, then fill in anything missing below.
        </span>
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
          Food name
        </span>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Oats" />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
          Amount (g)
        </span>
        <Input
          type="number"
          inputMode="decimal"
          value={amountStr}
          onChange={(e) => setAmountStr(e.target.value)}
        />
      </label>
      <p className="text-text-tertiary text-[11px]">Macros for the amount above.</p>
      <div className="grid grid-cols-4 gap-2">
        <ManualMacro label="kcal" value={kcal} onChange={setKcal} />
        <ManualMacro label="P" value={protein} onChange={setProtein} />
        <ManualMacro label="C" value={carbs} onChange={setCarbs} />
        <ManualMacro label="F" value={fat} onChange={setFat} />
      </div>
      <label className="text-text-secondary flex items-center gap-2 text-sm">
        <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} />
        Save as a custom food for next time
      </label>
      <div className="flex justify-end">
        <Button size="sm" disabled={!name.trim() || amount <= 0 || pending} onClick={submit}>
          {pending ? (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <Plus className="mr-1.5 h-4 w-4" aria-hidden />
          )}
          Add
        </Button>
      </div>
    </div>
  );
}

function ManualMacro({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-text-tertiary text-[10px] font-semibold uppercase">{label}</span>
      <Input
        type="number"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 text-sm"
        placeholder="0"
      />
    </label>
  );
}
