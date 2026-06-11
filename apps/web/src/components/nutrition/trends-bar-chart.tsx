"use client";

import dynamic from "next/dynamic";

import type { TrendsBarChartProps } from "./trends-bar-chart-impl";

export type { TrendsBar, TrendsBarChartProps } from "./trends-bar-chart-impl";

// Recharts is heavy — load the chart in its own client-only chunk.
const LazyChart = dynamic(
  () => import("./trends-bar-chart-impl").then((m) => m.TrendsBarChartImpl),
  { ssr: false, loading: () => null },
);

export function TrendsBarChart(props: TrendsBarChartProps) {
  const height = props.data.length === 0 ? 120 : (props.height ?? 220);
  return (
    <div style={{ height }} className="w-full">
      <LazyChart {...props} />
    </div>
  );
}
