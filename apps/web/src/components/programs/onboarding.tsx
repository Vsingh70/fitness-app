"use client";

import { useRouter } from "next/navigation";

/**
 * First-run programs onboarding. Shown when the user has zero programs. Two
 * editorial choice cards: Follow a template (ink fill, recommended) vs Build
 * your own (outline). Mirrors the nutrition onboarding card spec.
 */
export function ProgramsOnboarding() {
  const router = useRouter();

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col justify-center gap-8 py-10">
      <div className="text-center">
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.16em] uppercase">
          Welcome to programs
        </span>
        <h1 className="text-text mt-3 font-serif text-[34px] leading-tight font-medium tracking-tight">
          How do you want to train?
        </h1>
        <p className="text-text-secondary mx-auto mt-3 max-w-md text-[14px]">
          First time here — start from a proven template, or build your own. You can switch anytime.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <ChoiceCard
          variant="primary"
          kicker="Recommended"
          title="Follow a template"
          body="Pick a proven program — PPL, Upper/Lower, 5/3/1 and more. Copy it, tweak if you like, and start this week."
          cta="Browse templates →"
          onClick={() => router.push("/programs/templates")}
        />
        <ChoiceCard
          variant="outline"
          kicker="Full control"
          title="Build your own program"
          body="Compose days, exercises, set/rep schemes and a progression strategy from a blank slate."
          cta="Start building →"
          onClick={() => router.push("/programs/new")}
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
  onClick,
}: {
  variant: "primary" | "outline";
  kicker: string;
  title: string;
  body: string;
  cta: string;
  onClick: () => void;
}) {
  const primary = variant === "primary";
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "flex flex-col rounded-[6px] p-[22px] text-left transition-colors duration-150 ease-out " +
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
