"use client";

import { AlertCircle, ArrowLeft, Check } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PlanDayEditor } from "@/components/nutrition/plan-day-editor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToastStore } from "@/components/ui/toast";
import {
  CONTENT_MODE_LABEL,
  PLAN_KIND_LABEL,
  TRACKING_MODE_LABEL,
  dayRoleLabel,
  dayRolesForKind,
  num,
  type DayRole,
  type MealPlan,
  type MealPlanDay,
} from "@/lib/api/meal-plans";
import {
  useActivateMealPlan,
  useAddPlanDay,
  useMealPlan,
  useUpdateMealPlan,
  useUpdatePlanDay,
} from "@/lib/hooks/meal-plans";

export default function MealPlanEditorPage() {
  const params = useParams<{ id: string }>();
  const { data: plan, isLoading } = useMealPlan(params.id);
  const update = useUpdateMealPlan();
  const activate = useActivateMealPlan();
  const addDay = useAddPlanDay(params.id);
  const pushToast = useToastStore((s) => s.push);

  const [activeRole, setActiveRole] = useState<DayRole | null>(null);

  // Default the selected role to the first existing template once loaded.
  useEffect(() => {
    if (plan && activeRole === null) {
      setActiveRole(plan.day_templates[0]?.day_role ?? dayRolesForKind(plan.plan_kind)[0] ?? null);
    }
  }, [plan, activeRole]);

  if (isLoading || !plan) {
    return <p className="text-text-secondary py-10 text-center text-sm">Loading…</p>;
  }

  const roles = dayRolesForKind(plan.plan_kind);
  const byRole = new Map<DayRole, MealPlanDay>();
  for (const day of plan.day_templates) byRole.set(day.day_role, day);
  const role = activeRole ?? roles[0]!;
  const activeDay = byRole.get(role) ?? null;

  const ensureDay = async (target: DayRole) => {
    const existing = byRole.get(target);
    if (existing) return existing;
    return addDay.mutateAsync({ day_role: target });
  };

  const onSelectRole = async (target: DayRole) => {
    setActiveRole(target);
    if (!byRole.has(target)) {
      try {
        await ensureDay(target);
      } catch {
        pushToast({ kind: "error", message: "Could not add day template." });
      }
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        href="/nutrition/plans"
        className="text-text-secondary hover:text-text mb-4 inline-flex items-center gap-1 text-sm"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden /> Meal plans
      </Link>

      <header className="mb-5">
        <PlanNameField
          plan={plan}
          onSave={(name) => update.mutate({ id: plan.id, body: { name } })}
        />
        <p className="text-text-secondary mt-1 text-sm">
          {PLAN_KIND_LABEL[plan.plan_kind]} · {CONTENT_MODE_LABEL[plan.content_mode]} ·{" "}
          {TRACKING_MODE_LABEL[plan.tracking_mode]}
        </p>
        <div className="mt-3 flex gap-2">
          {plan.is_active ? (
            <span className="border-success text-success inline-flex items-center gap-1 rounded-[var(--radius-pill)] border px-2 py-1 text-[10px] font-semibold tracking-[0.06em] uppercase">
              <Check className="h-3 w-3" aria-hidden /> Active plan
            </span>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              disabled={activate.isPending}
              onClick={() =>
                activate.mutate(plan.id, {
                  onSuccess: () => pushToast({ kind: "success", message: "Plan activated" }),
                })
              }
            >
              Set active
            </Button>
          )}
        </div>
      </header>

      {/* Weekly review banner */}
      {plan.needs_week_review ? (
        <div className="border-accent/40 bg-accent-soft mb-5 flex items-start gap-2 rounded-[var(--radius-card)] border p-3">
          <AlertCircle className="text-accent mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-text text-sm font-medium">New week started</p>
            <p className="text-text-secondary mt-0.5 text-xs">
              Update this week&apos;s targets or meals, then mark it reviewed.
            </p>
            <Button
              size="sm"
              variant="secondary"
              className="mt-2"
              disabled={update.isPending}
              onClick={() =>
                update.mutate(
                  { id: plan.id, body: { needs_week_review: false } },
                  { onSuccess: () => pushToast({ kind: "success", message: "Marked reviewed" }) },
                )
              }
            >
              Mark reviewed
            </Button>
          </div>
        </div>
      ) : null}

      {/* Day role picker */}
      {roles.length > 1 ? (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {roles.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => onSelectRole(r)}
              className={
                "rounded-[var(--radius-pill)] border px-3 py-1 text-xs font-medium transition-colors " +
                (r === role
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border text-text-secondary hover:border-border-strong")
              }
            >
              {dayRoleLabel(r)}
              {!byRole.has(r) ? " +" : ""}
            </button>
          ))}
        </div>
      ) : null}

      {/* Per-day target overrides (when the plan carries targets) */}
      {plan.content_mode !== "meals_only" && activeDay ? (
        <DayTargets plan={plan} day={activeDay} key={`${activeDay.id}-targets`} />
      ) : null}

      {/* Active day editor */}
      {activeDay ? (
        <div className="mt-5">
          <PlanDayEditor plan={plan} day={activeDay} />
        </div>
      ) : (
        <div className="border-border-strong rounded-[var(--radius-card)] border border-dashed py-10 text-center">
          <p className="text-text-secondary text-sm">No template for {dayRoleLabel(role)} yet.</p>
          <Button
            size="sm"
            variant="secondary"
            className="mt-3"
            disabled={addDay.isPending}
            onClick={() => onSelectRole(role)}
          >
            Add {dayRoleLabel(role)} template
          </Button>
        </div>
      )}
    </div>
  );
}

function PlanNameField({ plan, onSave }: { plan: MealPlan; onSave: (name: string) => void }) {
  const [name, setName] = useState(plan.name);
  return (
    <input
      value={name}
      onChange={(e) => setName(e.target.value)}
      onBlur={() => {
        const next = name.trim() || plan.name;
        if (next !== plan.name) onSave(next);
      }}
      className="text-text w-full bg-transparent font-serif text-[26px] font-medium tracking-tight outline-none"
      aria-label="Plan name"
    />
  );
}

function DayTargets({ plan, day }: { plan: MealPlan; day: MealPlanDay }) {
  const updateDay = useUpdatePlanDay(plan.id);
  const showKcal = plan.tracking_mode !== "macros_only";
  const showMacros = plan.tracking_mode !== "calories_only";

  // Seed from the per-day override if present, else the effective target.
  const [kcal, setKcal] = useState(initial(day.target_kcal, day.effective_targets.target_kcal));
  const [p, setP] = useState(initial(day.target_protein_g, day.effective_targets.target_protein_g));
  const [c, setC] = useState(initial(day.target_carbs_g, day.effective_targets.target_carbs_g));
  const [f, setF] = useState(initial(day.target_fat_g, day.effective_targets.target_fat_g));

  const save = () =>
    updateDay.mutate({
      dayId: day.id,
      body: {
        target_kcal: kcal === "" ? null : num(kcal),
        target_protein_g: p === "" ? null : num(p),
        target_carbs_g: c === "" ? null : num(c),
        target_fat_g: f === "" ? null : num(f),
      },
    });

  return (
    <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-3">
      <p className="text-text-tertiary mb-2 text-[11px] font-semibold tracking-[0.08em] uppercase">
        {dayRoleLabel(day.day_role)} targets
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {showKcal ? (
          <TargetField label="kcal" value={kcal} onChange={setKcal} onBlur={save} />
        ) : null}
        {showMacros ? (
          <>
            <TargetField label="protein" value={p} onChange={setP} onBlur={save} />
            <TargetField label="carbs" value={c} onChange={setC} onBlur={save} />
            <TargetField label="fat" value={f} onChange={setF} onBlur={save} />
          </>
        ) : null}
      </div>
      {plan.content_mode === "targets_and_meals" ? (
        <p className="text-text-tertiary mt-2 text-[11px]">
          Leave blank to default to the summed meal totals.
        </p>
      ) : null}
    </div>
  );
}

function initial(override: string | null, effective: string | null): string {
  if (override != null) return String(Math.round(num(override)));
  if (effective != null) return String(Math.round(num(effective)));
  return "";
}

function TargetField({
  label,
  value,
  onChange,
  onBlur,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  onBlur: () => void;
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
        onBlur={onBlur}
        className="h-9 text-sm"
      />
    </label>
  );
}
