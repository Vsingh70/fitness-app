"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { TrendChart, type TrendPoint } from "@/components/charts/trend-chart";
import type { ReadinessDay } from "@/lib/api/readiness";
import { formatShortDate } from "@/lib/utils/format-weight";

interface Props {
  title: string;
  unit?: string;
  primaryLabel?: string;
  items: ReadinessDay[] | undefined;
  /** Pull the numeric value for this metric from a row; return null to drop the point. */
  mapValue: (day: ReadinessDay) => number | null;
  isLoading: boolean;
  isError: boolean;
}

export function MetricTrendCard({
  title,
  unit,
  primaryLabel,
  items,
  mapValue,
  isLoading,
  isError,
}: Props) {
  const points: TrendPoint[] = (items ?? [])
    .slice()
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0)) // OLDEST-FIRST for the x-axis
    .map((d) => {
      const v = mapValue(d);
      return v === null || !Number.isFinite(v) ? null : { date: formatShortDate(d.date), value: v };
    })
    .filter((p): p is TrendPoint => p !== null); // never substitute 0 for missing

  return (
    <Card>
      <CardHeader>{title}</CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-text-secondary text-sm">Loading…</p>
        ) : isError ? (
          <p className="text-destructive text-sm">Couldn&apos;t load trend.</p>
        ) : (
          <TrendChart kind="line" data={points} unit={unit} primaryLabel={primaryLabel ?? title} />
        )}
      </CardContent>
    </Card>
  );
}
