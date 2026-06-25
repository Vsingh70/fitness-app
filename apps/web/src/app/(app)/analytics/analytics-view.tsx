"use client";

import { useMemo, useState } from "react";

import { InsightCard } from "@/components/analytics/insight-card";
import { MuscleHeatmap } from "@/components/analytics/muscle-heatmap";
import { TrendChart, type TrendPoint } from "@/components/charts/trend-chart";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import type { VolumeResponse } from "@/lib/api/analytics";
import {
  useCurrentWeekVolume,
  useDismissInsight,
  useInsights,
  useVolume,
} from "@/lib/hooks/analytics";
import { useDeloadExercise } from "@/lib/hooks/programs";

const TREND_WEEKS = 8;

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Sum tonnage across all muscle series, bucketed by ISO year+week. */
function tonnageByWeek(volume: VolumeResponse | undefined): TrendPoint[] {
  if (!volume) return [];
  const buckets = new Map<string, { order: number; tonnage: number; week: number }>();
  for (const series of volume.items) {
    for (const p of series.points) {
      const key = `${p.iso_year}-${String(p.iso_week).padStart(2, "0")}`;
      const order = p.iso_year * 100 + p.iso_week;
      const prev = buckets.get(key);
      const tonnage = Number(p.tonnage_kg) || 0;
      if (prev) prev.tonnage += tonnage;
      else buckets.set(key, { order, tonnage, week: p.iso_week });
    }
  }
  return [...buckets.values()]
    .toSorted((a, b) => a.order - b.order)
    .map((b) => ({ date: `W${b.week}`, value: Math.round(b.tonnage) }));
}

function compactKg(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function AnalyticsView() {
  const today = useMemo(() => new Date(), []);
  const fromDate = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - TREND_WEEKS * 7);
    return d;
  }, [today]);

  const currentWeek = useCurrentWeekVolume();
  const volume = useVolume(isoDate(fromDate), isoDate(today));
  const insights = useInsights();
  const dismiss = useDismissInsight();
  const deload = useDeloadExercise();
  const [dismissingId, setDismissingId] = useState<string | null>(null);
  const [deloadingId, setDeloadingId] = useState<string | null>(null);

  const cw = currentWeek.data;
  const tonnageTrend = useMemo(() => tonnageByWeek(volume.data), [volume.data]);
  const insightItems = insights.data?.items ?? [];

  const onDismiss = (id: string) => {
    setDismissingId(id);
    dismiss.mutate(id, { onSettled: () => setDismissingId(null) });
  };

  const onDeload = (args: { insightId: string; programId: string; exerciseId: string }) => {
    setDeloadingId(args.insightId);
    deload.mutate(
      { programId: args.programId, exerciseId: args.exerciseId },
      {
        // Clear the resolved suggestion once the deload lands.
        onSuccess: () => dismiss.mutate(args.insightId),
        onSettled: () => setDeloadingId(null),
      },
    );
  };

  return (
    <RevealGroup className="page-shell flex flex-col" style={{ gap: "var(--space-section)" }}>
      <RevealItem>
        <header>
          <h1
            className="font-serif font-medium tracking-tight"
            style={{ fontSize: "var(--text-h2)" }}
          >
            Insights
          </h1>
          <p className="text-text-secondary mt-1.5 text-sm">
            Weekly volume, tonnage trend, and what to act on next.
          </p>
        </header>
      </RevealItem>

      {/* Stat grid */}
      <RevealItem className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Sets / wk" value={cw ? Math.round(Number(cw.total_working_sets)) : "—"} />
        <StatTile
          label="Tonnage / wk"
          value={cw ? compactKg(Math.round(Number(cw.total_tonnage_kg))) : "—"}
          unit="kg"
        />
        <StatTile label="Active insights" value={insights.isLoading ? "—" : insightItems.length} />
        <StatTile label="Training week" value={cw ? cw.iso_week : "—"} />
      </RevealItem>

      <RevealItem className="grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
        {/* Muscle-volume heatmap */}
        <Card className="overflow-hidden p-0">
          <CardHeader>
            <h2 className="text-base font-semibold tracking-normal normal-case">
              Volume by muscle
            </h2>
            <span className="text-text-tertiary text-[11px] tracking-normal normal-case">
              This week
            </span>
          </CardHeader>
          {currentWeek.isLoading ? (
            <div className="text-text-secondary px-4 pb-4 text-sm">Loading volume…</div>
          ) : currentWeek.isError ? (
            <div className="text-destructive px-4 pb-4 text-sm">Could not load volume.</div>
          ) : (
            <MuscleHeatmap perMuscle={cw?.per_muscle ?? []} />
          )}
        </Card>

        {/* Insights cards */}
        <Card className="p-0">
          <CardHeader>
            <h2 className="text-base font-semibold tracking-normal normal-case">Weekly insights</h2>
            <span className="text-text-tertiary text-[11px] tracking-normal normal-case">
              {insightItems.length} {insightItems.length === 1 ? "card" : "cards"}
            </span>
          </CardHeader>
          <div className="flex flex-col gap-3 px-[18px] pb-[18px]">
            {insights.isLoading ? (
              <p className="text-text-secondary text-sm">Loading insights…</p>
            ) : insights.isError ? (
              <p className="text-destructive text-sm">Could not load insights.</p>
            ) : insightItems.length === 0 ? (
              <p className="text-text-secondary text-sm">
                No active insights. Log a few more sessions and check back.
              </p>
            ) : (
              insightItems.map((insight) => (
                <InsightCard
                  key={insight.id}
                  insight={insight}
                  onDismiss={onDismiss}
                  dismissing={dismissingId === insight.id}
                  onDeload={onDeload}
                  deloading={deloadingId === insight.id}
                />
              ))
            )}
          </div>
        </Card>
      </RevealItem>

      {/* Tonnage trend */}
      <RevealItem>
        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold tracking-normal normal-case">
              Tonnage · {TREND_WEEKS} weeks
            </h2>
            <span className="text-text-tertiary text-[11px] tracking-normal normal-case">
              Total working tonnage per week
            </span>
          </CardHeader>
          <CardContent>
            {volume.isLoading ? (
              <p className="text-text-secondary text-sm">Loading trend…</p>
            ) : volume.isError ? (
              <p className="text-destructive text-sm">Could not load tonnage.</p>
            ) : (
              <TrendChart kind="bar" data={tonnageTrend} unit="kg" />
            )}
          </CardContent>
        </Card>
      </RevealItem>
    </RevealGroup>
  );
}
