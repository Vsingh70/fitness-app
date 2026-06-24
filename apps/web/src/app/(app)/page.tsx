"use client";

import { useMemo } from "react";

import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { InsightsFeed } from "@/components/today/insights-feed";
import { QuickMealLog } from "@/components/today/quick-meal-log";
import { ReadinessCard } from "@/components/today/readiness-card";
import { TodaySessionCard } from "@/components/today/today-session-card";
import { useMe } from "@/lib/hooks/me";
import { useReadinessHistory } from "@/lib/hooks/readiness";

function formatHeader(timezone: string): { kicker: string; pretty: string } {
  const now = new Date();
  const kicker = now.toLocaleDateString(undefined, { timeZone: timezone, weekday: "long" });
  const pretty = now.toLocaleDateString(undefined, {
    timeZone: timezone,
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  return { kicker, pretty };
}

/**
 * Today — the command center (page spec 04 "Today"). The daily landing surface
 * and the answer to "what do I do now": a readiness tile (from Health), today's
 * session card (the active program's current rotation slot, with Start), a quick
 * meal-log entry, and a short insights feed. Reads the program rotation and
 * links out to each surface. The tiles stagger in once on load via RevealGroup.
 */
export default function TodayPage() {
  const me = useMe();
  const timezone = me.data?.timezone ?? "UTC";

  // Latest scored day from the readiness window (order isn't guaranteed).
  const readiness = useReadinessHistory(7);
  const latestReadiness = useMemo(() => {
    const rows = (readiness.data?.items ?? [])
      .slice()
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    return rows.find((r) => r.score !== null) ?? null;
  }, [readiness.data]);

  const header = formatHeader(timezone);

  return (
    <div className="page-shell pb-10">
      <RevealGroup className="flex flex-col gap-[var(--space-section)]">
        <RevealItem>
          <header>
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
              {header.kicker}
            </span>
            <h1 className="text-text mt-1 font-serif text-[32px] font-medium tracking-tight md:text-[var(--text-h1)]">
              {header.pretty}
            </h1>
          </header>
        </RevealItem>

        <RevealItem>
          <div className="grid gap-4 md:grid-cols-[1fr_1.3fr] md:items-stretch">
            <ReadinessCard day={latestReadiness} isLoading={readiness.isLoading} />
            <TodaySessionCard />
          </div>
        </RevealItem>

        <RevealItem>
          <QuickMealLog />
        </RevealItem>

        <RevealItem>
          <InsightsFeed />
        </RevealItem>
      </RevealGroup>
    </div>
  );
}
