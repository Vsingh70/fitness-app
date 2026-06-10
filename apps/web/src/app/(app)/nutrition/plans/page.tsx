"use client";

import { AlertCircle, ArrowLeft, Check, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PlanCreateWizard } from "@/components/nutrition/plan-create-wizard";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import {
  CONTENT_MODE_LABEL,
  PLAN_KIND_LABEL,
  dayRoleLabel,
  targetsLine,
  type MealPlan,
  type MealPlanCreate,
} from "@/lib/api/meal-plans";
import {
  useActivateMealPlan,
  useCreateMealPlan,
  useDeleteMealPlan,
  useMealPlans,
  useUpdateMealPlan,
} from "@/lib/hooks/meal-plans";

export default function MealPlansPage() {
  const router = useRouter();
  const { data, isLoading, isError } = useMealPlans();
  const activate = useActivateMealPlan();
  const del = useDeleteMealPlan();
  const create = useCreateMealPlan();
  const update = useUpdateMealPlan();
  const pushToast = useToastStore((s) => s.push);

  const [wizardOpen, setWizardOpen] = useState(false);
  const plans = data?.items ?? [];

  const onCreate = async (body: MealPlanCreate) => {
    try {
      const plan = await create.mutateAsync(body);
      setWizardOpen(false);
      router.push(`/nutrition/plans/${plan.id}`);
    } catch {
      pushToast({ kind: "error", message: "Could not create plan." });
    }
  };

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
            Build daily, training and rest, or weekly plans. The active plan drives your daily
            targets.
          </p>
        </div>
        <Button size="sm" onClick={() => setWizardOpen(true)}>
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
            onClick={() => setWizardOpen(true)}
          >
            Create your first plan
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              onActivate={() =>
                activate.mutate(plan.id, {
                  onSuccess: () =>
                    pushToast({ kind: "success", message: `"${plan.name}" is now active` }),
                })
              }
              activating={activate.isPending}
              onDelete={() =>
                del.mutate(plan.id, {
                  onSuccess: () => pushToast({ kind: "info", message: "Plan deleted" }),
                })
              }
              onClearReview={() =>
                update.mutate(
                  { id: plan.id, body: { needs_week_review: false } },
                  {
                    onSuccess: () =>
                      pushToast({ kind: "success", message: "Marked this week as reviewed" }),
                  },
                )
              }
            />
          ))}
        </div>
      )}

      <PlanCreateWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreate={onCreate}
        pending={create.isPending}
      />
    </div>
  );
}

function PlanCard({
  plan,
  onActivate,
  activating,
  onDelete,
  onClearReview,
}: {
  plan: MealPlan;
  onActivate: () => void;
  activating: boolean;
  onDelete: () => void;
  onClearReview: () => void;
}) {
  return (
    <div className="border-border bg-surface-elevated rounded-[var(--radius-card)] border p-4">
      <div className="flex items-start justify-between gap-3">
        <Link href={`/nutrition/plans/${plan.id}`} className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-text text-base font-semibold">{plan.name}</span>
            {plan.is_active ? (
              <span className="border-success text-success inline-flex items-center gap-1 rounded-[var(--radius-pill)] border px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.06em] uppercase">
                <Check className="h-2.5 w-2.5" aria-hidden /> Active
              </span>
            ) : null}
          </div>
          <p className="text-text-secondary mt-1 text-xs">
            {PLAN_KIND_LABEL[plan.plan_kind]} · {CONTENT_MODE_LABEL[plan.content_mode]}
          </p>
        </Link>
        <button
          type="button"
          aria-label="Delete plan"
          onClick={onDelete}
          className="text-text-tertiary hover:text-destructive p-1"
        >
          <Trash2 className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {/* Day templates + their totals */}
      <div className="mt-3 flex flex-col gap-1">
        {plan.day_templates.map((day) => (
          <div
            key={day.id}
            className="text-text-secondary flex items-center justify-between gap-2 text-xs tabular-nums"
          >
            <span className="text-text-tertiary font-medium">{dayRoleLabel(day.day_role)}</span>
            <span>{targetsLine(day.effective_targets, plan.tracking_mode)}</span>
          </div>
        ))}
        {plan.day_templates.length === 0 ? (
          <p className="text-text-tertiary text-xs">No day templates yet.</p>
        ) : null}
      </div>

      {/* Weekly review prompt */}
      {plan.needs_week_review ? (
        <div className="border-accent/40 bg-accent-soft mt-3 flex items-start gap-2 rounded-[var(--radius-card)] border p-3">
          <AlertCircle className="text-accent mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-text text-sm font-medium">New week started</p>
            <p className="text-text-secondary mt-0.5 text-xs">
              Review and update this week&apos;s targets or meals before they go live.
            </p>
            <div className="mt-2 flex gap-2">
              <Link href={`/nutrition/plans/${plan.id}`}>
                <Button size="sm" variant="secondary">
                  Review targets
                </Button>
              </Link>
              <Button size="sm" variant="ghost" onClick={onClearReview}>
                Looks good
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="mt-3 flex gap-2">
        {!plan.is_active ? (
          <Button size="sm" variant="secondary" onClick={onActivate} disabled={activating}>
            Set active
          </Button>
        ) : null}
        <Link href={`/nutrition/plans/${plan.id}`}>
          <Button size="sm" variant="ghost">
            Edit
          </Button>
        </Link>
      </div>
    </div>
  );
}
