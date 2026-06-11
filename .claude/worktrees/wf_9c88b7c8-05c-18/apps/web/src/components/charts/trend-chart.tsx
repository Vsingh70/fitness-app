"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface TrendPoint {
  date: string;
  value: number;
  /** Optional overlay value (e.g. compared exercise's e1RM). */
  overlay?: number;
}

interface TrendChartProps {
  kind: "line" | "bar";
  data: TrendPoint[];
  unit?: string;
  height?: number;
  overlayLabel?: string;
  primaryLabel?: string;
}

const TICK_COLOR = "var(--color-text-tertiary)";
const GRID_COLOR = "var(--color-border)";
const ACCENT = "var(--color-accent)";
const OVERLAY = "var(--color-pr)";

export function TrendChart({
  kind,
  data,
  unit,
  height = 220,
  overlayLabel,
  primaryLabel = "value",
}: TrendChartProps) {
  if (data.length === 0) {
    return (
      <div className="text-text-secondary flex h-[120px] items-center justify-center text-sm">
        No data yet.
      </div>
    );
  }

  const formatValue = (v: unknown) => {
    const num = typeof v === "number" ? v : Number(v);
    if (!Number.isFinite(num)) return "-";
    return unit ? `${num} ${unit}` : String(num);
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      {kind === "line" ? (
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <CartesianGrid stroke={GRID_COLOR} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: TICK_COLOR, fontSize: 11 }} stroke={GRID_COLOR} />
          <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} stroke={GRID_COLOR} width={40} />
          <Tooltip
            contentStyle={{
              background: "var(--color-surface-elevated)",
              border: `1px solid ${GRID_COLOR}`,
              borderRadius: "var(--radius-button)",
              color: "var(--color-text)",
              fontSize: 12,
            }}
            formatter={(value) => formatValue(value)}
          />
          <Line
            name={primaryLabel}
            type="monotone"
            dataKey="value"
            stroke={ACCENT}
            strokeWidth={1.6}
            dot={false}
          />
          {overlayLabel ? (
            <Line
              name={overlayLabel}
              type="monotone"
              dataKey="overlay"
              stroke={OVERLAY}
              strokeWidth={1.6}
              strokeDasharray="4 4"
              dot={false}
            />
          ) : null}
        </LineChart>
      ) : (
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
          <CartesianGrid stroke={GRID_COLOR} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: TICK_COLOR, fontSize: 11 }} stroke={GRID_COLOR} />
          <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} stroke={GRID_COLOR} width={40} />
          <Tooltip
            contentStyle={{
              background: "var(--color-surface-elevated)",
              border: `1px solid ${GRID_COLOR}`,
              borderRadius: "var(--radius-button)",
              color: "var(--color-text)",
              fontSize: 12,
            }}
            formatter={(value) => formatValue(value)}
          />
          <Bar dataKey="value" fill={ACCENT} radius={[3, 3, 0, 0]} />
        </BarChart>
      )}
    </ResponsiveContainer>
  );
}
