"use client";

import dynamic from "next/dynamic";

import type { TrendChartProps } from "./trend-chart-impl";

export type { TrendChartProps, TrendPoint } from "./trend-chart-impl";

// Recharts is heavy — load the actual chart in its own client-only chunk so
// it stays out of the shared bundle.
const LazyTrendChart = dynamic(() => import("./trend-chart-impl").then((m) => m.TrendChartImpl), {
  ssr: false,
  loading: () => null,
});

export function TrendChart(props: TrendChartProps) {
  // Reserve the chart's height while the chunk loads to avoid layout shift
  // (the impl renders a 120px empty state when there is no data).
  const height = props.data.length === 0 ? 120 : (props.height ?? 220);
  return (
    <div style={{ height }} className="w-full">
      <LazyTrendChart {...props} />
    </div>
  );
}
