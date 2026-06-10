"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { InsightResponse, InsightSeverity, InsightKind } from "@/lib/api/analytics";
import { cn } from "@/lib/cn";

/**
 * Severity -> left border accent. The API enum is info | warn | action; the
 * prototype's info/notice/warning bands map to success / accent / warning.
 */
const SEVERITY_BORDER: Record<InsightSeverity, string> = {
  info: "border-l-success",
  warn: "border-l-warning",
  action: "border-l-accent",
};

const KIND_LABEL: Record<InsightKind, string> = {
  stagnation: "Plateau",
  volume_drop: "Volume drop",
  frequency_drop: "Frequency drop",
  pr_streak: "PR streak",
  weak_muscle: "Weak point",
  strong_muscle: "Strong point",
  imbalance: "Imbalance",
  undertrained: "Undertrained",
};

/** Kinds that warrant a program tweak deep-link into the program editor. */
const PROGRAM_KINDS: ReadonlySet<InsightKind> = new Set<InsightKind>([
  "weak_muscle",
  "strong_muscle",
  "imbalance",
  "undertrained",
  "volume_drop",
  "frequency_drop",
]);

interface DeepLink {
  href: string;
  label: string;
}

/** Build a deep-link CTA from the insight kind/subject. */
function deepLinkFor(insight: InsightResponse): DeepLink {
  if (PROGRAM_KINDS.has(insight.kind)) {
    return { href: "/programs", label: "Adjust program" };
  }
  // stagnation / pr_streak target a specific lift; the subject is an exercise
  // slug. Until a slug route exists, send to the workouts history hub.
  return { href: "/workouts", label: "View exercise" };
}

/** Reactive per-lift deload payload (continuous mode stagnation insight). */
interface DeloadAction {
  programId: string;
  exerciseId: string;
}

/**
 * A continuous-mode stagnation insight carries a `deload_exercise` suggested
 * action plus the `program_id`/`exercise_id` to act on. Returns null when the
 * insight is not an actionable per-lift deload.
 */
function deloadActionFor(insight: InsightResponse): DeloadAction | null {
  const payload = insight.payload as {
    suggested_action?: unknown;
    program_id?: unknown;
    exercise_id?: unknown;
  };
  if (payload.suggested_action !== "deload_exercise") return null;
  if (typeof payload.program_id !== "string" || typeof payload.exercise_id !== "string") {
    return null;
  }
  return { programId: payload.program_id, exerciseId: payload.exercise_id };
}

interface InsightCardProps {
  insight: InsightResponse;
  onDismiss: (id: string) => void;
  dismissing?: boolean;
  /** Apply a reactive per-lift deload for a continuous-program stagnation. */
  onDeload?: (args: { insightId: string; programId: string; exerciseId: string }) => void;
  deloading?: boolean;
}

export function InsightCard({
  insight,
  onDismiss,
  dismissing,
  onDeload,
  deloading,
}: InsightCardProps) {
  const deload = deloadActionFor(insight);
  const cta = deepLinkFor(insight);
  const text = insight.rationale ?? insight.body;
  return (
    <div
      className={cn(
        "bg-surface-elevated flex flex-col gap-1.5 rounded-[var(--radius-card)] border-l-[3px] p-4",
        SEVERITY_BORDER[insight.severity],
      )}
    >
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
        {KIND_LABEL[insight.kind]}
      </span>
      <div className="text-[15px] font-semibold tracking-[-0.005em]">{insight.title}</div>
      {text ? <p className="text-text-secondary text-[13px] leading-relaxed">{text}</p> : null}
      <div className="mt-2 flex gap-2">
        {deload && onDeload ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              onDeload({
                insightId: insight.id,
                programId: deload.programId,
                exerciseId: deload.exerciseId,
              })
            }
            disabled={deloading || dismissing}
          >
            {deloading ? "Applying..." : "Apply deload"}
          </Button>
        ) : (
          <Link
            href={cta.href}
            className={cn(
              "inline-flex items-center justify-center gap-2 rounded-[var(--radius-button)] font-semibold tracking-[0.01em]",
              "transition-[background-color,color,filter,transform] duration-150 ease-out active:scale-[0.985]",
              "h-[34px] rounded-md px-[14px] text-[13px]",
              "border-text text-text hover:bg-text hover:text-bg border bg-transparent",
            )}
          >
            {cta.label}
          </Link>
        )}
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onDismiss(insight.id)}
          disabled={dismissing || deloading}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}
