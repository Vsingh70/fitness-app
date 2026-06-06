"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeft, Plus } from "lucide-react";

import { PlanMealEditor } from "@/components/nutrition/plan-meal-editor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UnderlineTabs } from "@/components/ui/tabs";
import { useToastStore } from "@/components/ui/toast";
import {
  dayMacros,
  emptyDays,
  parseDays,
  type DayStructure,
  type PlanDays,
  type PlannedDay,
  type PlannedMeal,
} from "@/lib/api/meal-plans";
import { useMealPlans, useUpdateMealPlan } from "@/lib/hooks/meal-plans";

const STRUCTURE_TABS = [
  { value: "single" as const, label: "Single day" },
  { value: "weekdays" as const, label: "Weekdays" },
  { value: "day_types" as const, label: "Day types" },
];

export default function MealPlanEditorPage() {
  const params = useParams<{ id: string }>();
  const { data, isLoading } = useMealPlans();
  const update = useUpdateMealPlan();
  const pushToast = useToastStore((s) => s.push);

  const plan = data?.items.find((p) => p.id === params.id);

  // Local editable copy.
  const [name, setName] = useState<string | null>(null);
  const [targets, setTargets] = useState<{ kcal: string; p: string; c: string; f: string } | null>(
    null,
  );
  const [days, setDays] = useState<PlanDays | null>(null);
  const [activeDayKey, setActiveDayKey] = useState<string | null>(null);

  // Initialize from the loaded plan once.
  const initialized = name !== null;
  if (!initialized && plan) {
    setName(plan.name);
    setTargets({
      kcal: String(Math.round(Number(plan.target_kcal))),
      p: String(Math.round(Number(plan.target_protein_g))),
      c: String(Math.round(Number(plan.target_carbs_g))),
      f: String(Math.round(Number(plan.target_fat_g))),
    });
    const parsed = parseDays(plan.days);
    setDays(parsed);
    setActiveDayKey(parsed.days[0]?.key ?? null);
  }

  const activeDay = useMemo(
    () => days?.days.find((d) => d.key === activeDayKey) ?? days?.days[0] ?? null,
    [days, activeDayKey],
  );

  if (isLoading || !plan || !days || !targets || name === null) {
    return <p className="text-text-secondary py-10 text-center text-sm">Loading…</p>;
  }

  const num = (s: string) => {
    const x = Number(s);
    return Number.isFinite(x) && x >= 0 ? x : 0;
  };

  const save = async () => {
    try {
      await update.mutateAsync({
        id: plan.id,
        body: {
          name: name.trim() || plan.name,
          target_kcal: num(targets.kcal),
          target_protein_g: num(targets.p),
          target_carbs_g: num(targets.c),
          target_fat_g: num(targets.f),
          days: days as unknown as Record<string, never>,
        },
      });
      pushToast({ kind: "success", message: "Plan saved" });
    } catch {
      pushToast({ kind: "error", message: "Could not save plan." });
    }
  };

  const switchStructure = (structure: DayStructure) => {
    if (structure === days.structure) return;
    // Switching structure resets the day skeleton (keeps it predictable).
    const next = emptyDays(structure);
    setDays(next);
    setActiveDayKey(next.days[0]?.key ?? null);
  };

  const updateActiveDay = (updater: (d: PlannedDay) => PlannedDay) => {
    setDays((prev) =>
      prev
        ? { ...prev, days: prev.days.map((d) => (d.key === activeDay?.key ? updater(d) : d)) }
        : prev,
    );
  };

  const addMeal = () => {
    updateActiveDay((d) => ({
      ...d,
      meals: [
        ...d.meals,
        {
          label: `Meal ${d.meals.length + 1}`,
          kcal: 0,
          protein_g: 0,
          carbs_g: 0,
          fat_g: 0,
          items: [],
        },
      ],
    }));
  };

  const setMeal = (idx: number, meal: PlannedMeal) =>
    updateActiveDay((d) => ({ ...d, meals: d.meals.map((m, i) => (i === idx ? meal : m)) }));

  const removeMeal = (idx: number) =>
    updateActiveDay((d) => ({ ...d, meals: d.meals.filter((_, i) => i !== idx) }));

  const addDayType = () => {
    setDays((prev) => {
      if (!prev) return prev;
      const n = prev.days.length + 1;
      return {
        ...prev,
        days: [...prev.days, { key: `day_${n}_${Date.now()}`, label: `Day type ${n}`, meals: [] }],
      };
    });
  };

  const dm = activeDay ? dayMacros(activeDay) : { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href="/nutrition/plans"
        className="text-text-secondary hover:text-text mb-4 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden /> Meal plans
      </Link>

      {/* Name + targets */}
      <header className="mb-6">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="text-text w-full bg-transparent font-serif text-[26px] font-medium tracking-tight outline-none"
          aria-label="Plan name"
        />
        <div className="mt-3 grid grid-cols-4 gap-2">
          <TargetField
            label="kcal"
            value={targets.kcal}
            onChange={(v) => setTargets({ ...targets, kcal: v })}
          />
          <TargetField
            label="protein"
            value={targets.p}
            onChange={(v) => setTargets({ ...targets, p: v })}
          />
          <TargetField
            label="carbs"
            value={targets.c}
            onChange={(v) => setTargets({ ...targets, c: v })}
          />
          <TargetField
            label="fat"
            value={targets.f}
            onChange={(v) => setTargets({ ...targets, f: v })}
          />
        </div>
      </header>

      {/* Structure picker */}
      <UnderlineTabs
        tabs={STRUCTURE_TABS}
        value={days.structure}
        onChange={(v) => switchStructure(v)}
        ariaLabel="Day structure"
      />

      {/* Day tabs (for weekdays / day_types) */}
      {days.structure !== "single" ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {days.days.map((d) => (
            <button
              key={d.key}
              type="button"
              onClick={() => setActiveDayKey(d.key)}
              className={
                "rounded-[var(--radius-pill)] border px-3 py-1 text-xs font-medium transition-colors " +
                (d.key === activeDay?.key
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border text-text-secondary hover:border-border-strong")
              }
            >
              {d.label}
            </button>
          ))}
          {days.structure === "day_types" ? (
            <button
              type="button"
              onClick={addDayType}
              className="border-border-strong text-text-secondary hover:text-text rounded-[var(--radius-pill)] border border-dashed px-3 py-1 text-xs font-medium"
            >
              + Day type
            </button>
          ) : null}
        </div>
      ) : null}

      {/* Active day editor */}
      {activeDay ? (
        <div className="mt-5">
          {days.structure === "day_types" ? (
            <Input
              value={activeDay.label}
              onChange={(e) => updateActiveDay((d) => ({ ...d, label: e.target.value }))}
              className="mb-3"
              aria-label="Day type name"
            />
          ) : null}

          <div className="text-text-tertiary mb-3 flex items-center justify-between text-xs tabular-nums">
            <span className="font-semibold tracking-[0.08em] uppercase">
              {activeDay.label} · planned total
            </span>
            <span>
              {Math.round(dm.kcal)} kcal · {Math.round(dm.protein_g)}p · {Math.round(dm.carbs_g)}c ·{" "}
              {Math.round(dm.fat_g)}f
            </span>
          </div>

          <div className="flex flex-col gap-3">
            {activeDay.meals.map((meal, idx) => (
              <PlanMealEditor
                key={idx}
                meal={meal}
                onChange={(m) => setMeal(idx, m)}
                onRemove={() => removeMeal(idx)}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={addMeal}
            className="border-border-strong text-text-secondary hover:text-text mt-3 flex w-full items-center justify-center gap-1.5 rounded-[var(--radius-button)] border border-dashed py-2.5 text-sm font-medium"
          >
            <Plus className="h-4 w-4" aria-hidden /> Add meal
          </button>
        </div>
      ) : null}

      {/* Save bar */}
      <div className="mt-8 flex justify-end">
        <Button onClick={save} disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save plan"}
        </Button>
      </div>
    </div>
  );
}

function TargetField({
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
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      <Input
        type="number"
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 text-sm"
      />
    </label>
  );
}
