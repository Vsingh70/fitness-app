"use client";

import { useRouter } from "next/navigation";

import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useUpdateMe } from "@/lib/hooks/me";

/**
 * First-run nutrition onboarding. Shown when `me.nutrition_mode == null`.
 * Two editorial choice cards: Flexible tracking (ink fill, recommended) vs
 * Create a meal plan (outline). Choosing persists the mode via PATCH /me; the
 * page re-renders the day screen once the field is set.
 */
export function NutritionOnboarding() {
  const router = useRouter();
  const updateMe = useUpdateMe();
  const pushToast = useToastStore((s) => s.push);

  const choose = (mode: "flexible" | "plan") =>
    updateMe.mutate(
      { nutrition_mode: mode },
      {
        onSuccess: () => {
          // Plan-mode users go to the existing plan-create flow; flexible users
          // stay here and the page re-renders the day screen.
          if (mode === "plan") router.push("/nutrition/plans");
        },
        onError: (e) =>
          pushToast({
            kind: "error",
            message: (e as unknown as ApiError)?.message ?? "Couldn't save your choice.",
          }),
      },
    );

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col justify-center gap-8 py-10">
      <div className="text-center">
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.16em] uppercase">
          Welcome to nutrition
        </span>
        <h1 className="text-text mt-3 font-serif text-[34px] leading-tight font-medium tracking-tight">
          How do you want to track?
        </h1>
        <p className="text-text-secondary mx-auto mt-3 max-w-md text-[14px]">
          First time here — pick a way to get started. You can switch anytime in settings.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <ChoiceCard
          variant="primary"
          kicker="Recommended"
          title="Flexible tracking"
          body="Log meals freely as you eat — search foods or scan a barcode. Add as many meals a day as you like. No setup."
          cta="Start tracking →"
          disabled={updateMe.isPending}
          onClick={() => choose("flexible")}
        />
        <ChoiceCard
          variant="outline"
          kicker="Structured"
          title="Create a meal plan"
          body="Build a daily template with a set number of meals and macro targets, then log against it each day."
          cta="Build a plan →"
          disabled={updateMe.isPending}
          onClick={() => choose("plan")}
        />
      </div>
    </div>
  );
}

function ChoiceCard({
  variant,
  kicker,
  title,
  body,
  cta,
  disabled,
  onClick,
}: {
  variant: "primary" | "outline";
  kicker: string;
  title: string;
  body: string;
  cta: string;
  disabled: boolean;
  onClick: () => void;
}) {
  const primary = variant === "primary";
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={
        "flex flex-col rounded-[6px] p-[22px] text-left transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-60 " +
        (primary ? "bg-text text-bg" : "border-border-strong hover:border-text text-text border")
      }
    >
      <span
        className={
          "text-[11px] font-semibold tracking-[0.14em] uppercase " +
          (primary ? "text-bg/70" : "text-text-tertiary")
        }
      >
        {kicker}
      </span>
      <span className="mt-3 font-serif text-[26px] font-medium tracking-tight">{title}</span>
      <span className={"mt-2 text-[13px] " + (primary ? "text-bg/80" : "text-text-secondary")}>
        {body}
      </span>
      <span className="mt-5 text-[12px] font-semibold tracking-[0.1em] uppercase">{cta}</span>
    </button>
  );
}
