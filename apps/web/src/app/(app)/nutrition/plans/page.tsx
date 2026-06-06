"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Check, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useToastStore } from "@/components/ui/toast";
import { emptyDays, type MealPlanCreate } from "@/lib/api/meal-plans";
import {
  useActivateMealPlan,
  useCreateMealPlan,
  useDeleteMealPlan,
  useMealPlans,
} from "@/lib/hooks/meal-plans";

export default function MealPlansPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useMealPlans();
  const activate = useActivateMealPlan();
  const del = useDeleteMealPlan();
  const create = useCreateMealPlan();
  const pushToast = useToastStore((s) => s.push);

  const [createOpen, setCreateOpen] = useState(false);
  const plans = data?.items ?? [];

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href="/nutrition"
        className="text-text-secondary hover:text-text mb-4 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden /> Nutrition
      </Link>

      <header className="mb-6 flex items-end justify-between gap-3">
        <div>
          <p className="text-text-tertiary text-[11px] font-semibold tracking-[0.12em] uppercase">
            Nutrition
          </p>
          <h1 className="font-serif text-[28px] font-medium tracking-tight">Meal plans</h1>
          <p className="text-text-secondary mt-1 text-sm">
            Set macro targets and plan your meals. The active plan drives your daily targets.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" aria-hidden />
          New plan
        </Button>
      </header>

      {isLoading ? (
        <p className="text-text-secondary py-8 text-center text-sm">Loading…</p>
      ) : isError ? (
        <p className="text-destructive py-8 text-center text-sm">Couldn&apos;t load plans.</p>
      ) : plans.length === 0 ? (
        <div className="border-border-strong rounded-[var(--radius-card)] border border-dashed py-12 text-center">
          <p className="text-text-secondary text-sm">No meal plans yet.</p>
          <Button
            size="sm"
            variant="secondary"
            className="mt-3"
            onClick={() => setCreateOpen(true)}
          >
            Create your first plan
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {plans.map((p) => (
            <div
              key={p.id}
              className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <Link href={`/nutrition/plans/${p.id}`} className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-text text-base font-semibold">{p.name}</span>
                    {p.is_active ? (
                      <span className="border-success text-success inline-flex items-center gap-1 rounded-[var(--radius-pill)] border px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.06em] uppercase">
                        <Check className="h-2.5 w-2.5" aria-hidden /> Active
                      </span>
                    ) : null}
                  </div>
                  <p className="text-text-secondary mt-1 text-xs tabular-nums">
                    {Math.round(Number(p.target_kcal))} kcal ·{" "}
                    {Math.round(Number(p.target_protein_g))}p ·{" "}
                    {Math.round(Number(p.target_carbs_g))}c · {Math.round(Number(p.target_fat_g))}f
                  </p>
                </Link>
                <button
                  type="button"
                  aria-label="Delete plan"
                  onClick={() => {
                    del.mutate(p.id, {
                      onSuccess: () => pushToast({ kind: "info", message: "Plan deleted" }),
                    });
                  }}
                  className="text-text-tertiary hover:text-destructive p-1"
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                {!p.is_active ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      activate.mutate(p.id, {
                        onSuccess: () =>
                          pushToast({ kind: "success", message: `"${p.name}" is now active` }),
                      })
                    }
                    disabled={activate.isPending}
                  >
                    Set active
                  </Button>
                ) : null}
                <Link href={`/nutrition/plans/${p.id}`}>
                  <Button size="sm" variant="ghost">
                    Edit
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreatePlanSheet
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreate={async (body) => {
          try {
            const plan = await create.mutateAsync(body);
            setCreateOpen(false);
            router.push(`/nutrition/plans/${plan.id}`);
          } catch {
            pushToast({ kind: "error", message: "Could not create plan." });
          }
        }}
        pending={create.isPending}
      />
    </div>
  );
}

function CreatePlanSheet({
  open,
  onClose,
  onCreate,
  pending,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (body: MealPlanCreate) => void;
  pending: boolean;
}) {
  const [name, setName] = useState("");
  const [kcal, setKcal] = useState("2200");
  const [protein, setProtein] = useState("180");
  const [carbs, setCarbs] = useState("220");
  const [fat, setFat] = useState("70");

  const num = (s: string) => {
    const x = Number(s);
    return Number.isFinite(x) && x >= 0 ? x : 0;
  };

  const submit = () => {
    if (!name.trim()) return;
    onCreate({
      name: name.trim(),
      target_kcal: num(kcal),
      target_protein_g: num(protein),
      target_carbs_g: num(carbs),
      target_fat_g: num(fat),
      // Start with a single repeating day; structure is editable in the editor.
      days: emptyDays("single") as unknown as Record<string, never>,
    });
  };

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title="New meal plan">
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
            Plan name
          </span>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Lean bulk"
            autoFocus
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <MacroInput label="Calories" value={kcal} onChange={setKcal} unit="kcal" />
          <MacroInput label="Protein" value={protein} onChange={setProtein} unit="g" />
          <MacroInput label="Carbs" value={carbs} onChange={setCarbs} unit="g" />
          <MacroInput label="Fat" value={fat} onChange={setFat} unit="g" />
        </div>
        <div className="mt-1 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={pending}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} disabled={!name.trim() || pending}>
            {pending ? "Creating…" : "Create & edit"}
          </Button>
        </div>
      </div>
    </Sheet>
  );
}

function MacroInput({
  label,
  value,
  onChange,
  unit,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  unit: string;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
        {label} ({unit})
      </span>
      <Input
        type="number"
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
