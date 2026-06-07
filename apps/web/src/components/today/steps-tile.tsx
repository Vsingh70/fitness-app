"use client";

import Link from "next/link";

import type { ReadinessDay } from "@/lib/api/readiness";
import { formatSteps } from "@/lib/utils/format-health";

interface Props {
  data: ReadinessDay[] | undefined;
  isLoading: boolean;
}

export function StepsTile({ data, isLoading }: Props) {
  // history is returned for a date range; order is not guaranteed — sort newest-first by date.
  const rows = (data ?? [])
    .slice()
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  const withSteps = rows.filter((r) => (r.steps ?? null) !== null);
  const latest = withSteps[0] ?? null;
  const latestSteps = latest?.steps ?? null;

  // 7-day avg over the days BEFORE the latest, so "vs 7-day avg" is a true
  // comparison (today isn't averaged against itself).
  const prior = withSteps.slice(1, 8);
  const avg =
    prior.length > 0 ? prior.reduce((s, r) => s + (r.steps ?? 0), 0) / prior.length : null;

  return (
    <Link
      href="/health"
      className="border-border bg-surface-elevated hover:border-border-strong flex flex-col gap-1 rounded-[var(--radius-card)] border p-5 transition-colors"
    >
      <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
        Steps
      </span>
      <span className="text-text font-serif text-3xl font-medium tracking-tight tabular-nums">
        {isLoading ? "—" : latestSteps !== null ? formatSteps(latestSteps) : "—"}
      </span>
      {!isLoading && latestSteps === null ? (
        <>
          <span className="text-text-secondary text-sm">No data yet</span>
          <span className="text-text-tertiary text-xs">Syncs from your watch →</span>
        </>
      ) : avg !== null ? (
        <span className="text-text-tertiary text-xs">{`vs ${formatSteps(avg)} 7-day avg`}</span>
      ) : null}
    </Link>
  );
}
