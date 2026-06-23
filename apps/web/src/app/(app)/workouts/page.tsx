"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ExerciseLibrary } from "@/components/exercise/exercise-library";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { TrainTodayCard } from "@/components/workouts/train-today-card";
import { Card, CardContent } from "@/components/ui/card";
import { UnderlineTabs } from "@/components/ui/tabs";
import { useMe } from "@/lib/hooks/me";
import { useSessionHistory } from "@/lib/hooks/workouts";
import { isoDayInTz } from "@/lib/workouts/history";
import type { WorkoutSessionListItem } from "@/lib/workouts/types";

type HubTab = "train" | "library";

interface WeekBucket {
  weekStart: string;
  label: string;
  items: WorkoutSessionListItem[];
}

function bucketByWeek(items: WorkoutSessionListItem[], timezone: string): WeekBucket[] {
  const map = new Map<string, WorkoutSessionListItem[]>();
  for (const item of items) {
    const day = isoDayInTz(item.started_at, timezone);
    const monday = mondayOf(day);
    if (!map.has(monday)) map.set(monday, []);
    map.get(monday)!.push(item);
  }
  return [...map.entries()]
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([weekStart, list]) => ({
      weekStart,
      label: prettyWeek(weekStart),
      items: list.sort(
        (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
      ),
    }));
}

function mondayOf(yyyyMmDd: string): string {
  const [y, m, d] = yyyyMmDd.split("-").map((s) => Number.parseInt(s, 10));
  const date = new Date(Date.UTC(y!, m! - 1, d!, 12));
  const dow = date.getUTCDay();
  const diff = (dow + 6) % 7;
  date.setUTCDate(date.getUTCDate() - diff);
  return date.toISOString().slice(0, 10);
}

function prettyWeek(weekStart: string): string {
  const [y, m, d] = weekStart.split("-").map((s) => Number.parseInt(s, 10));
  const date = new Date(Date.UTC(y!, m! - 1, d!, 12));
  return `Week of ${date.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" })}`;
}

function durationMin(started_at: string, ended_at: string | null): number | null {
  if (!ended_at) return null;
  return Math.max(
    0,
    Math.round((new Date(ended_at).getTime() - new Date(started_at).getTime()) / 60000),
  );
}

export default function WorkoutsPage() {
  const [tab, setTab] = useState<HubTab>("train");

  return (
    <RevealGroup
      className="page-shell flex flex-col"
      style={{ gap: "var(--space-section)" }}
    >
      <RevealItem>
        <header className="flex items-end justify-between gap-4">
          <div>
            <h1
              className="font-serif font-medium tracking-tight"
              style={{ fontSize: "var(--text-h2)" }}
            >
              Workouts
            </h1>
            <p className="text-text-secondary mt-1.5 text-sm">
              Start today’s session, review your history, and browse the exercise library.
            </p>
          </div>
          <Link
            href="/calendar"
            className="text-text-secondary hover:text-text border-border-strong inline-flex h-[32px] shrink-0 items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.08em] uppercase"
          >
            Calendar
          </Link>
        </header>
      </RevealItem>

      <RevealItem>
        <UnderlineTabs
          tabs={[
            { value: "train", label: "Train" },
            { value: "library", label: "Library" },
          ]}
          value={tab}
          onChange={(v) => setTab(v as HubTab)}
          ariaLabel="Workouts sections"
        />
      </RevealItem>

      {tab === "train" ? (
        <RevealItem>
          <TrainTab />
        </RevealItem>
      ) : (
        <RevealItem>
          <section aria-label="Exercise library">
            <ExerciseLibrary showHeader={false} />
          </section>
        </RevealItem>
      )}
    </RevealGroup>
  );
}

function TrainTab() {
  const me = useMe();
  const history = useSessionHistory(25);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const items = useMemo(() => history.data?.pages.flatMap((p) => p.items) ?? [], [history.data]);
  const timezone = me.data?.timezone ?? "UTC";
  const buckets = useMemo(() => bucketByWeek(items, timezone), [items, timezone]);

  const onIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      if (entries[0]?.isIntersecting && history.hasNextPage && !history.isFetchingNextPage) {
        void history.fetchNextPage();
      }
    },
    [history],
  );

  useEffect(() => {
    if (!sentinelRef.current) return;
    const observer = new IntersectionObserver(onIntersect, { rootMargin: "200px" });
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [onIntersect]);

  return (
    <div className="flex flex-col gap-6">
      <TrainTodayCard />

      <section>
        <h2 className="text-text-secondary mb-3 text-[13px] font-semibold tracking-[0.1em] uppercase">
          Recent history
        </h2>

        {history.isLoading ? (
          <p className="text-text-secondary">Loading…</p>
        ) : history.isError ? (
          <p className="text-destructive">Could not load sessions.</p>
        ) : items.length === 0 ? (
          <Card>
            <CardContent>
              <p className="text-text-secondary text-sm">
                No sessions yet. Start today’s session above to see it here.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col gap-6">
            {buckets.map((bucket) => (
              <div key={bucket.weekStart}>
                <h3 className="text-text-tertiary mb-3 text-[11px] font-semibold tracking-[0.14em] uppercase">
                  {bucket.label}
                </h3>
                <ul className="flex flex-col gap-2">
                  {bucket.items.map((item) => {
                    const dur = durationMin(item.started_at, item.ended_at);
                    const finished = !!item.ended_at;
                    return (
                      <li key={item.id}>
                        <Link
                          href={`/workouts/${item.id}`}
                          className="hover:bg-surface border-border flex items-center justify-between gap-3 rounded-[var(--radius-button)] border px-3 py-2"
                        >
                          <div className="flex min-w-0 flex-col">
                            <span className="text-text truncate font-medium">
                              {item.name ?? "Untitled session"}
                            </span>
                            <span className="text-text-tertiary text-xs">
                              {new Date(item.started_at).toLocaleString(undefined, {
                                timeZone: timezone,
                                weekday: "short",
                                month: "short",
                                day: "numeric",
                                hour: "numeric",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                          <div className="text-text-secondary flex shrink-0 items-center gap-3 text-xs">
                            {dur !== null ? (
                              <span className="font-serif text-[13px] tabular-nums">{dur} min</span>
                            ) : null}
                            {!finished ? (
                              <span className="text-accent inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                                In progress
                              </span>
                            ) : null}
                          </div>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
            <div ref={sentinelRef} className="h-1" />
            {history.isFetchingNextPage ? (
              <p className="text-text-tertiary text-center text-xs">Loading more…</p>
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
