"use client";

import Link from "next/link";

import { useInsights } from "@/lib/hooks/analytics";
import type { InsightResponse, InsightKind, InsightSeverity } from "@/lib/api/analytics";
import { cn } from "@/lib/cn";

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

const SEVERITY_BORDER: Record<InsightSeverity, string> = {
  info: "border-l-success",
  warn: "border-l-warning",
  action: "border-l-accent",
};

/** Kinds whose adjustment writes back to the active program (deep-link to Programs). */
const PROGRAM_KINDS: ReadonlySet<InsightKind> = new Set<InsightKind>([
  "weak_muscle",
  "strong_muscle",
  "imbalance",
  "undertrained",
  "volume_drop",
  "frequency_drop",
]);

/** Deep-link target for a feed card: program adjustment vs. exercise/history. */
function deepLinkFor(insight: InsightResponse): { href: string; label: string } {
  if (PROGRAM_KINDS.has(insight.kind)) return { href: "/programs", label: "Adjust program" };
  return { href: "/analytics", label: "View detail" };
}

/**
 * The command center's short insights feed: the top 1–3 active recommendation
 * cards from `useInsights`, each deep-linking to the relevant surface (Programs
 * for program-adjusting kinds, Insights otherwise). Read-only here — the full
 * dismiss/apply affordances live on the Insights page.
 */
export function InsightsFeed() {
  const insights = useInsights();

  if (insights.isLoading || insights.isError) return null;
  const items = (insights.data?.items ?? []).slice(0, 3);
  if (items.length === 0) return null;

  return (
    <section>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-text-secondary text-[13px] font-semibold tracking-[0.1em] uppercase">
          Insights
        </span>
        <Link
          href="/analytics"
          className="text-accent text-[12px] font-medium hover:brightness-110"
        >
          View all →
        </Link>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {items.map((insight) => {
          const cta = deepLinkFor(insight);
          const text = insight.rationale ?? insight.body;
          return (
            <Link
              key={insight.id}
              href={cta.href}
              className={cn(
                "bg-surface-elevated hover:border-text/30 flex flex-col gap-1.5 rounded-[var(--radius-card)] border border-l-[3px] border-transparent p-4 transition-colors duration-150 ease-out",
                SEVERITY_BORDER[insight.severity],
              )}
            >
              <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
                {KIND_LABEL[insight.kind]}
              </span>
              <span className="text-[15px] font-semibold tracking-[-0.005em]">{insight.title}</span>
              {text ? (
                <p className="text-text-secondary line-clamp-2 text-[13px] leading-relaxed">
                  {text}
                </p>
              ) : null}
              <span className="text-accent mt-auto pt-2 text-[11px] font-semibold tracking-[0.06em] uppercase">
                {cta.label} →
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
