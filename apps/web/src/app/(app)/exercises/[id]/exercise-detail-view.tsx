"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { TrendChart, type TrendPoint } from "@/components/charts/trend-chart";
import { ExerciseHero } from "@/components/exercise/exercise-hero";
import { PredictedNextStrip } from "@/components/exercise/predicted-next-strip";
import { PrTileRow } from "@/components/exercise/pr-tile-row";
import { VariantsList } from "@/components/exercise/variants-list";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { UnderlineTabs } from "@/components/ui/tabs";
import { useExerciseAnalytics } from "@/lib/hooks/analytics";
import { cn } from "@/lib/cn";
import type { components } from "@/lib/api/types";

type TimeSeriesPoint = components["schemas"]["TimeSeriesPointResponse"];
type ScatterPoint = components["schemas"]["ScatterPointResponse"];

type WindowKey = "4w" | "12w" | "6mo" | "1y" | "all";
type TabKey = "trends" | "sets" | "variants";

const WINDOWS: { value: WindowKey; label: string }[] = [
  { value: "4w", label: "4w" },
  { value: "12w", label: "12w" },
  { value: "6mo", label: "6mo" },
  { value: "1y", label: "1y" },
  { value: "all", label: "All" },
];

const TABS = [
  { value: "trends" as const, label: "Trends" },
  { value: "sets" as const, label: "Sets" },
  { value: "variants" as const, label: "Variants" },
];

function n(value: string | number): number {
  const x = typeof value === "number" ? value : Number(value);
  return Number.isFinite(x) ? x : 0;
}

function toTrendPoints(series: TimeSeriesPoint[]): TrendPoint[] {
  return series.map((p) => ({ date: p.session_date, value: n(p.value) }));
}

const ROWS_PER_PAGE = 25;

export function ExerciseDetailView({ id }: { id: string }) {
  const [window, setWindow] = useState<WindowKey>("12w");
  const [tab, setTab] = useState<TabKey>("trends");
  const [tablePage, setTablePage] = useState(0);

  const analytics = useExerciseAnalytics(id, window);

  const e1rmPoints = useMemo<TrendPoint[]>(
    () => (analytics.data ? toTrendPoints(analytics.data.e1rm_series) : []),
    [analytics.data],
  );
  const volumePoints = useMemo<TrendPoint[]>(
    () => (analytics.data ? toTrendPoints(analytics.data.volume_series) : []),
    [analytics.data],
  );

  const sortedScatter = useMemo<ScatterPoint[]>(() => {
    const items = analytics.data?.set_scatter ?? [];
    return items.toSorted((a, b) => b.session_date.localeCompare(a.session_date));
  }, [analytics.data]);

  const totalPages = Math.max(1, Math.ceil(sortedScatter.length / ROWS_PER_PAGE));
  const pagedScatter = sortedScatter.slice(
    tablePage * ROWS_PER_PAGE,
    (tablePage + 1) * ROWS_PER_PAGE,
  );

  if (analytics.isLoading) return <p className="text-text-secondary">Loading exercise…</p>;
  if (analytics.isError || !analytics.data)
    return <p className="text-destructive">Could not load exercise analytics.</p>;

  const a = analytics.data;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 pb-10">
      <Link
        href="/workouts"
        className="text-text-tertiary hover:text-text text-[11px] font-semibold tracking-[0.14em] uppercase"
      >
        ← Back to workouts
      </Link>

      <ExerciseHero exercise={a.exercise} />

      <PredictedNextStrip predicted={a.predicted_next_session} />

      <PrTileRow recentPrs={a.recent_prs} setScatter={a.set_scatter} />

      <div className="flex items-center justify-between gap-3">
        <UnderlineTabs tabs={TABS} value={tab} onChange={setTab} ariaLabel="Exercise tabs" />
        <div className="flex gap-1">
          {WINDOWS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setWindow(value)}
              data-testid={`range-${value}`}
              aria-pressed={window === value}
              className={cn(
                "inline-flex h-[26px] items-center rounded-[var(--radius-pill)] border px-[10px] text-[10px] font-semibold tracking-[0.1em] uppercase",
                window === value
                  ? "text-accent border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)]"
                  : "border-border-strong text-text-secondary hover:text-text",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "trends" ? (
        <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
          <Card>
            <CardHeader>
              <span>Estimated 1RM</span>
              <span className="text-text-tertiary text-[11px] font-normal tracking-normal normal-case">
                Brzycki · {a.window} window
              </span>
            </CardHeader>
            <CardContent>
              <TrendChart kind="line" data={e1rmPoints} unit="kg" primaryLabel="e1RM" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <span>Working volume</span>
              <span className="text-text-tertiary text-[11px] font-normal tracking-normal normal-case">
                kg per session
              </span>
            </CardHeader>
            <CardContent>
              <TrendChart kind="bar" data={volumePoints} unit="kg" />
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "sets" ? (
        <Card>
          <CardHeader>
            <span>All sets</span>
            <span className="text-text-tertiary text-[11px] font-normal tracking-normal normal-case">
              {sortedScatter.length} set{sortedScatter.length === 1 ? "" : "s"} · {a.window}
            </span>
          </CardHeader>
          <CardContent className="px-0">
            {sortedScatter.length === 0 ? (
              <p className="text-text-secondary px-[18px] pt-2 text-sm">No sets in this range.</p>
            ) : (
              <table className="w-full text-sm tabular-nums">
                <thead>
                  <tr className="border-border-strong text-text-tertiary border-b text-[10px] font-semibold tracking-[0.1em] uppercase">
                    <th className="px-4 py-3 text-left">Date</th>
                    <th className="px-2 py-3 text-right">Weight</th>
                    <th className="px-2 py-3 text-right">Reps</th>
                    <th className="px-2 py-3 pr-4 text-right">RPE</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedScatter.map((s, idx) => (
                    <tr
                      key={`${s.session_date}-${idx}`}
                      className={cn(
                        "border-border border-b last:border-b-0",
                        s.is_pr ? "bg-pr-soft" : "",
                      )}
                    >
                      <td
                        className={cn(
                          "px-4 py-3",
                          s.is_pr ? "border-pr border-l-[3px] pl-3 font-medium" : "",
                        )}
                      >
                        {s.session_date}
                      </td>
                      <td className="px-2 py-3 text-right font-serif">{n(s.weight_kg)}</td>
                      <td className="px-2 py-3 text-right font-serif">{s.reps}</td>
                      <td className="px-2 py-3 pr-4 text-right font-serif">
                        {s.rpe ? n(s.rpe) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {totalPages > 1 ? (
              <div className="border-border mt-1 flex items-center justify-between border-t px-4 py-3 text-[12px]">
                <button
                  type="button"
                  disabled={tablePage === 0}
                  onClick={() => setTablePage((p) => Math.max(0, p - 1))}
                  className="text-text-secondary hover:text-text font-semibold tracking-[0.08em] uppercase disabled:opacity-40"
                >
                  ← Previous
                </button>
                <span className="text-text-tertiary">
                  Page {tablePage + 1} of {totalPages}
                </span>
                <button
                  type="button"
                  disabled={tablePage + 1 >= totalPages}
                  onClick={() => setTablePage((p) => Math.min(totalPages - 1, p + 1))}
                  className="text-text-secondary hover:text-text font-semibold tracking-[0.08em] uppercase disabled:opacity-40"
                >
                  Next →
                </button>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {tab === "variants" ? <VariantsList variants={a.suggested_variants} /> : null}
    </div>
  );
}
