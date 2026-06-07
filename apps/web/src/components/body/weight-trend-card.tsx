"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { TrendChart, type TrendPoint } from "@/components/charts/trend-chart";
import type { components } from "@/lib/api/types";
import { kgToDisplay, formatShortDate, toNum, weightUnitLabel } from "@/lib/utils/format-weight";

type UnitSystem = components["schemas"]["UnitSystem"];
type BodyMetricTrend = components["schemas"]["BodyMetricTrendResponse"];

interface Props {
  data: BodyMetricTrend | undefined;
  isLoading: boolean;
  isError: boolean;
  unit: UnitSystem | undefined;
}

export function WeightTrendCard({ data, isLoading, isError, unit }: Props) {
  const series = data?.series.find((s) => s.metric === "weight_kg");
  // Trend points are OLDEST-FIRST already — map in order, no reverse.
  const points: TrendPoint[] = (series?.points ?? [])
    .map((p) => {
      const raw = toNum(p.moving_average) ?? toNum(p.value); // prefer smoothed, fall back to weekly mean
      const v = kgToDisplay(raw, unit); // unit-convert + round1
      return v === null ? null : { date: formatShortDate(p.week_start), value: v };
    })
    .filter((p): p is TrendPoint => p !== null); // drop all-null weeks — NEVER substitute 0

  return (
    <Card>
      <CardHeader>Weight trend</CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-text-secondary text-sm">Loading…</p>
        ) : isError ? (
          <p className="text-destructive text-sm">Couldn&apos;t load trend.</p>
        ) : (
          <TrendChart
            kind="line"
            data={points}
            unit={weightUnitLabel(unit)}
            primaryLabel="Weight"
          />
        )}
      </CardContent>
    </Card>
  );
}
