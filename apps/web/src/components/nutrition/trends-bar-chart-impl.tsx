"use client";

import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface TrendsBar {
  label: string;
  kcal: number;
  /** True for the day currently being viewed (rendered in clay). */
  today: boolean;
}

export interface TrendsBarChartProps {
  data: TrendsBar[];
  target: number;
  height?: number;
}

const TICK = "var(--color-text-tertiary)";
const GRID = "var(--color-border)";
const ACCENT = "var(--color-accent)";
const INK = "var(--color-text)";
const MUTED = "var(--color-border-strong)";

/** Color a bar: today is clay, over-target is ink, under-target is muted. */
function barFill(bar: TrendsBar, target: number): string {
  if (bar.today) return ACCENT;
  if (target > 0 && bar.kcal > target) return INK;
  return MUTED;
}

export function TrendsBarChartImpl({ data, target, height = 220 }: TrendsBarChartProps) {
  if (data.length === 0) {
    return (
      <div className="text-text-secondary flex h-[120px] items-center justify-center text-sm">
        No data yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: TICK, fontSize: 11 }} stroke={GRID} />
        <YAxis tick={{ fill: TICK, fontSize: 11 }} stroke={GRID} width={44} />
        <Tooltip
          cursor={{ fill: "var(--color-surface)" }}
          contentStyle={{
            background: "var(--color-surface-elevated)",
            border: `1px solid ${GRID}`,
            borderRadius: "var(--radius-button)",
            color: "var(--color-text)",
            fontSize: 12,
          }}
          formatter={(value) => [`${Math.round(Number(value))} kcal`, "Intake"]}
        />
        {target > 0 ? (
          <ReferenceLine
            y={target}
            stroke={TICK}
            strokeDasharray="4 4"
            label={{ value: "Target", position: "right", fill: TICK, fontSize: 10 }}
          />
        ) : null}
        <Bar dataKey="kcal" radius={[3, 3, 0, 0]}>
          {data.map((bar) => (
            <Cell key={bar.label} fill={barFill(bar, target)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
