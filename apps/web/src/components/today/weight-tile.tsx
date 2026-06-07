"use client";

import Link from "next/link";

import type { BodyMetric } from "@/lib/api/body-metrics";
import { useMe } from "@/lib/hooks/me";
import { formatWeight, toNum, weeklyDelta, weightUnitLabel } from "@/lib/utils/format-weight";

interface Props {
  data: BodyMetric[] | undefined;
  isLoading: boolean;
}

export function WeightTile({ data, isLoading }: Props) {
  const unit = useMe().data?.unit_system; // undefined-safe (defaults metric in helpers)
  const items = data ?? [];
  const latest = items.find((r) => toNum(r.weight_kg) !== null) ?? null;
  const valueStr = isLoading ? "—" : latest ? formatWeight(latest.weight_kg, unit) : null;
  const delta = weeklyDelta(items, unit);

  return (
    <Link
      href="/body"
      className="border-border bg-surface-elevated hover:border-border-strong flex flex-col gap-1 rounded-[var(--radius-card)] border p-5 transition-colors"
    >
      <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
        Weight
      </span>
      <span className="text-text font-serif text-3xl font-medium tracking-tight tabular-nums">
        {valueStr ?? "—"}
      </span>
      {!isLoading && latest === null ? (
        <>
          <span className="text-text-secondary text-sm">No data yet</span>
          <span className="text-text-tertiary text-xs">Log in Body →</span>
        </>
      ) : delta ? (
        <span className="text-text-tertiary text-xs">
          {`${delta.displayDelta >= 0 ? "+" : "−"}${Math.abs(delta.displayDelta)} ${weightUnitLabel(unit)} this week`}
        </span>
      ) : null}
    </Link>
  );
}
