"use client";

import Link from "next/link";

import type { ReadinessDay } from "@/lib/api/readiness";
import { formatSleep } from "@/lib/utils/format-health";

interface Props {
  data: ReadinessDay[] | undefined;
  isLoading: boolean;
}

export function SleepTile({ data, isLoading }: Props) {
  const rows = (data ?? [])
    .slice()
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  const latest = rows.find((r) => (r.sleep_minutes ?? null) !== null) ?? null;
  const minutes = latest?.sleep_minutes ?? null;

  return (
    <Link
      href="/health"
      className="border-border bg-surface-elevated hover:border-border-strong flex flex-col gap-1 rounded-[var(--radius-card)] border p-5 transition-colors"
    >
      <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
        Sleep
      </span>
      <span className="text-text font-serif text-3xl font-medium tracking-tight tabular-nums">
        {isLoading ? "—" : minutes !== null ? formatSleep(minutes) : "—"}
      </span>
      {!isLoading && minutes === null ? (
        <>
          <span className="text-text-secondary text-sm">No data yet</span>
          <span className="text-text-tertiary text-xs">Syncs from your watch →</span>
        </>
      ) : minutes !== null ? (
        <span className="text-text-tertiary text-xs">Last night</span>
      ) : null}
    </Link>
  );
}
