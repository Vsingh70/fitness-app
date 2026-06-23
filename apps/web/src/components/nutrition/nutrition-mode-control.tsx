"use client";

import { Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { CONTENT_MODE_LABEL, PLAN_KIND_LABEL, type MealPlan } from "@/lib/api/meal-plans";
import { useActivateMealPlan, useMealPlans } from "@/lib/hooks/meal-plans";
import { useUpdateMe } from "@/lib/hooks/me";

type Mode = "flexible" | "plan";

/**
 * The day-header mode switch (04 §Nutrition). `nutritionMode` is an account
 * preference, switchable freely from here and from Settings.
 *
 * - Flexible → plan: if a plan is already active, just flip the mode. Otherwise
 *   prompt to pick which plan to activate; with no plans, route to the create
 *   wizard. We always return in plan mode.
 * - Plan → flexible: flip the mode; the day reverts to free-form meals.
 *
 * Switching is non-destructive: meals logged today are never deleted — the day
 * screen re-presents them under the new mode. This control only writes the
 * preference (and, when entering plan mode with no active plan, activates one).
 */
export function NutritionModeControl({ mode }: { mode: Mode }) {
  const router = useRouter();
  const pushToast = useToastStore((s) => s.push);
  const updateMe = useUpdateMe();
  const plans = useMealPlans();
  const activate = useActivateMealPlan();

  const [pickOpen, setPickOpen] = useState(false);

  const allPlans = plans.data?.items ?? [];
  const hasActivePlan = allPlans.some((p) => p.is_active);

  const setMode = (next: Mode) =>
    updateMe.mutate(
      { nutrition_mode: next },
      {
        onError: (e) =>
          pushToast({
            kind: "error",
            message: (e as unknown as ApiError)?.message ?? "Couldn't switch mode.",
          }),
      },
    );

  const toFlexible = () => {
    if (mode === "flexible") return;
    setMode("flexible");
  };

  const toPlan = () => {
    if (mode === "plan") return;
    // A plan is already active — flip straight into plan mode.
    if (hasActivePlan) {
      setMode("plan");
      return;
    }
    // No plan to log against yet: pick one, or build one first.
    if (allPlans.length === 0) {
      pushToast({ kind: "info", message: "Build a meal plan to track in plan mode." });
      router.push("/nutrition/plans");
      return;
    }
    setPickOpen(true);
  };

  const choosePlan = async (plan: MealPlan) => {
    try {
      if (!plan.is_active) await activate.mutateAsync(plan.id);
      await updateMe.mutateAsync({ nutrition_mode: "plan" });
      setPickOpen(false);
      pushToast({ kind: "success", message: `Tracking against "${plan.name}"` });
    } catch (e) {
      pushToast({
        kind: "error",
        message: (e as unknown as ApiError)?.message ?? "Couldn't switch to that plan.",
      });
    }
  };

  const busy = updateMe.isPending || activate.isPending;

  return (
    <>
      <div
        role="radiogroup"
        aria-label="Nutrition tracking mode"
        className="border-border bg-surface inline-flex rounded-[var(--radius-button)] border p-[3px]"
      >
        <ModeButton
          label="Flexible"
          active={mode === "flexible"}
          disabled={busy}
          onClick={toFlexible}
        />
        <ModeButton label="Plan" active={mode === "plan"} disabled={busy} onClick={toPlan} />
      </div>

      <Sheet open={pickOpen} onOpenChange={setPickOpen} title="Pick a plan to track against">
        <p className="text-text-secondary mb-4 text-[13px]">
          Switching to plan mode logs against an active plan&apos;s meals and targets. Nothing you
          logged today is lost — your meals carry over.
        </p>
        <div className="flex flex-col gap-2">
          {allPlans.map((plan) => (
            <button
              key={plan.id}
              type="button"
              disabled={busy}
              onClick={() => choosePlan(plan)}
              className="border-border hover:border-border-strong flex items-center justify-between gap-3 rounded-[var(--radius-card)] border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="min-w-0">
                <span className="text-text block text-sm font-semibold">{plan.name}</span>
                <span className="text-text-secondary mt-0.5 block text-xs">
                  {PLAN_KIND_LABEL[plan.plan_kind]} · {CONTENT_MODE_LABEL[plan.content_mode]}
                </span>
              </span>
              {plan.is_active ? (
                <span className="text-success inline-flex shrink-0 items-center gap-1 text-[10px] font-semibold tracking-[0.06em] uppercase">
                  <Check className="h-3 w-3" aria-hidden /> Active
                </span>
              ) : null}
            </button>
          ))}
        </div>
        <div className="mt-5 flex items-center justify-between gap-2">
          <Button variant="ghost" size="sm" onClick={() => router.push("/nutrition/plans")}>
            New plan
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setPickOpen(false)} disabled={busy}>
            Cancel
          </Button>
        </div>
      </Sheet>
    </>
  );
}

function ModeButton({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      disabled={disabled}
      onClick={onClick}
      className={
        "rounded-md px-3 py-1 text-[11px] font-semibold tracking-[0.04em] transition-colors disabled:cursor-not-allowed disabled:opacity-50 " +
        (active
          ? "bg-surface-elevated text-text shadow-[var(--shadow-1)]"
          : "text-text-secondary hover:text-text")
      }
    >
      {label}
    </button>
  );
}
