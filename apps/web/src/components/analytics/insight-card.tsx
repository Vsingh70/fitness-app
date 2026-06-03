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

interface InsightCardProps {
  insight: InsightResponse;
  onDismiss: (id: string) => void;
  dismissing?: boolean;
}

export function InsightCard({ insight, onDismiss, dismissing }: InsightCardProps) {
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
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onDismiss(insight.id)}
          disabled={dismissing}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}
