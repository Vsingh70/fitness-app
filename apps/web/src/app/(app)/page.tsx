"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { NutritionStrip } from "@/components/today/nutrition-strip";
import { ReadinessTile } from "@/components/today/readiness-tile";
import { RecommendationCard } from "@/components/today/recommendation-card";
import { ScheduledHero } from "@/components/today/scheduled-hero";
import { SleepTile } from "@/components/today/sleep-tile";
import { StepsTile } from "@/components/today/steps-tile";
import { WeightTile } from "@/components/today/weight-tile";
import { StatTile } from "@/components/ui/stat-tile";
import { useBodyMetrics } from "@/lib/hooks/body-metrics";
import { useMe } from "@/lib/hooks/me";
import { useReadinessHistory } from "@/lib/hooks/readiness";
import {
  useNutritionTargets,
  useNutritionToday,
  useReadinessToday,
  useRecommendations,
  useScheduledRange,
} from "@/lib/hooks/today";
import { useCreateEmptySession, useRecentSessions, useSessionHistory } from "@/lib/hooks/workouts";
import { useActiveSession } from "@/lib/state/active-session";
import { isoDayInTz } from "@/lib/workouts/history";

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

function weekStartIso(now: Date): string {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const dow = d.getUTCDay();
  const diff = (dow + 6) % 7;
  d.setUTCDate(d.getUTCDate() - diff);
  return d.toISOString().slice(0, 10);
}

function weekEndIso(weekStart: string): string {
  const [y, m, d] = weekStart.split("-").map((s) => Number.parseInt(s, 10));
  const date = new Date(Date.UTC(y!, m! - 1, d!));
  date.setUTCDate(date.getUTCDate() + 6);
  return date.toISOString().slice(0, 10);
}

export default function TodayPage() {
  const me = useMe();
  const timezone = me.data?.timezone ?? "UTC";

  const today = useMemo(() => isoDayInTz(new Date().toISOString(), timezone), [timezone]);
  const weekStart = useMemo(() => weekStartIso(new Date()), []);
  const weekEnd = useMemo(() => weekEndIso(weekStart), [weekStart]);

  const readiness = useReadinessToday();
  const bodyMetrics = useBodyMetrics();
  const readinessHistory = useReadinessHistory(7);
  const recommendations = useRecommendations();
  const nutritionTotals = useNutritionToday(today);
  const nutritionTargets = useNutritionTargets();
  const scheduled = useScheduledRange(today, today);
  const weekHistory = useSessionHistory(50);
  const recent = useRecentSessions(5);
  const activeSessionId = useActiveSession((s) => s.activeSessionId);

  const todayScheduled = scheduled.data?.items.find(
    (s) => s.scheduled_for === today && s.status === "planned",
  );

  const weekSessionCount = useMemo(() => {
    const items = weekHistory.data?.pages.flatMap((p) => p.items) ?? [];
    return items.filter((s) => {
      const day = isoDayInTz(s.started_at, timezone);
      return day >= weekStart && day <= weekEnd;
    }).length;
  }, [weekHistory.data, timezone, weekStart, weekEnd]);

  const header = formatHeader(timezone);
  const recItems = recommendations.data?.items ?? [];
  const recentItems = recent.data?.items ?? [];
  const lastSessionName = recentItems[0]?.name ?? "—";

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8 pb-6">
      <header>
        <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
          {header.kicker}
        </span>
        <h1 className="mt-1 font-serif text-[32px] font-medium tracking-tight">{header.pretty}</h1>
      </header>

      <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-1">
          <ReadinessTile data={readiness.data} isLoading={readiness.isLoading} />
          <WeightTile data={bodyMetrics.data?.items} isLoading={bodyMetrics.isLoading} />
          <StepsTile data={readinessHistory.data?.items} isLoading={readinessHistory.isLoading} />
          <SleepTile data={readinessHistory.data?.items} isLoading={readinessHistory.isLoading} />
        </div>
        <NutritionStrip totals={nutritionTotals.data} targets={nutritionTargets.data} />
      </div>

      <section>
        <ScheduledHero scheduled={todayScheduled} />
      </section>

      {recItems.length > 0 ? (
        <section>
          <SectionHead title="Recommendations" detail="From this week's progression engine" />
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {recItems.slice(0, 3).map((rec) => (
              <RecommendationCard key={rec.id} rec={rec} />
            ))}
          </div>
        </section>
      ) : null}

      <section>
        <SectionHead title="This week" link={{ href: "/analytics", label: "View insights →" }} />
        <div className="mt-3 grid gap-6 sm:grid-cols-3">
          <StatTile label="Sessions" value={weekSessionCount} unit="this week" />
          <StatTile label="Last logged" value={lastSessionName} />
          <StatTile label="Active session" value={activeSessionId ? "In progress" : "None"} />
        </div>
      </section>

      <RecentSessionsList />
    </div>
  );
}

function SectionHead({
  title,
  detail,
  link,
}: {
  title: string;
  detail?: string;
  link?: { href: string; label: string };
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-text-secondary text-[13px] font-semibold tracking-[0.1em] uppercase">
        {title}
      </span>
      {link ? (
        <Link href={link.href} className="text-accent text-[12px] font-medium hover:brightness-110">
          {link.label}
        </Link>
      ) : detail ? (
        <span className="text-text-tertiary text-[12px]">{detail}</span>
      ) : null}
    </div>
  );
}

function RecentSessionsList() {
  const recent = useRecentSessions(5);
  const router = useRouter();
  const createEmpty = useCreateEmptySession();
  const setActive = useActiveSession((s) => s.setActive);

  if (recent.isLoading || recent.isError) return null;
  const items = recent.data?.items ?? [];

  const onStartEmpty = () => {
    createEmpty.mutate(
      {},
      {
        onSuccess: (session) => {
          setActive(session.id, session.started_at);
          router.push(`/workouts/${session.id}`);
        },
      },
    );
  };

  return (
    <section>
      <SectionHead title="Recent sessions" link={{ href: "/workouts", label: "All sessions →" }} />
      {items.length === 0 ? (
        <p className="text-text-secondary mt-3 text-sm">
          No sessions yet. Start an empty workout below or pick a scheduled day above.
        </p>
      ) : (
        <ul className="mt-3 flex flex-col">
          {items.slice(0, 5).map((s) => (
            <li key={s.id}>
              <Link
                href={`/workouts/${s.id}`}
                className="border-border hover:bg-surface flex items-center justify-between gap-3 border-b py-3 last:border-b-0"
              >
                <div className="flex min-w-0 flex-col">
                  <span className="text-text truncate text-sm font-medium">
                    {s.name ?? "Untitled session"}
                  </span>
                  <span className="text-text-tertiary text-xs">
                    {new Date(s.started_at).toLocaleString(undefined, {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <span className="text-text-tertiary text-[11px] tracking-[0.08em] uppercase">
                  Open →
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4">
        <button
          type="button"
          onClick={onStartEmpty}
          disabled={createEmpty.isPending}
          data-testid="start-empty-workout"
          className="text-text-secondary hover:text-text text-[12px] font-semibold tracking-[0.08em] uppercase disabled:opacity-60"
        >
          {createEmpty.isPending ? "Starting…" : "Start empty workout"}
        </button>
      </div>
    </section>
  );
}
