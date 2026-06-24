"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";
import type { ReadinessDay } from "@/lib/api/readiness";

interface Props {
  /** Latest day from the readiness history (most recent first or last — caller resolves). */
  day: ReadinessDay | null;
  isLoading: boolean;
}

const BAND_COPY: Record<
  NonNullable<ReadinessDay["band"]>,
  { copy: string; tone: string; ring: string }
> = {
  high: { copy: "Push it", tone: "text-success", ring: "stroke-[var(--color-success)]" },
  moderate: { copy: "Workable", tone: "text-warning", ring: "stroke-[var(--color-warning)]" },
  low: { copy: "Take it easy", tone: "text-destructive", ring: "stroke-[var(--color-destructive)]" },
};

const R = 40;
const CIRC = 2 * Math.PI * R;

/**
 * Today's readiness tile, fed by `useReadinessHistory`. With a scored day it
 * shows the ring + band copy; with no wearable data it falls back to a quiet
 * "Connect" state deep-linking to Health (the readiness source per the IA).
 */
export function ReadinessCard({ day, isLoading }: Props) {
  const score = day?.score ?? null;
  const band = day?.band ?? null;
  const hasData = score !== null;
  const fraction = score !== null ? Math.max(0, Math.min(1, score / 100)) : 0;
  const dash = CIRC * (1 - fraction);
  const meta = band ? BAND_COPY[band] : null;

  if (!isLoading && !hasData) {
    return (
      <Link
        href="/health"
        className="border-border bg-surface-elevated hover:border-text flex h-full items-center gap-5 rounded-[var(--radius-card)] border p-5 transition-colors duration-150 ease-out"
      >
        <div className="border-border-strong text-text-tertiary grid h-[96px] w-[96px] shrink-0 place-items-center rounded-full border border-dashed">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 21s-7-4.35-9.5-9C1 9 2.5 5 6 5c2 0 3.2 1.2 4 2.5C10.8 6.2 12 5 14 5c3.5 0 5 4 3.5 7-2.5 4.65-9.5 9-9.5 9z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
            Readiness
          </span>
          <span className="text-text text-[15px] font-semibold">Connect a wearable</span>
          <span className="text-text-tertiary text-xs">
            Sync sleep + HRV in Health to score your day →
          </span>
        </div>
      </Link>
    );
  }

  return (
    <div className="border-border bg-surface-elevated flex h-full items-center gap-5 rounded-[var(--radius-card)] border p-5">
      <div className="relative h-[96px] w-[96px] shrink-0">
        <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
          <circle cx="48" cy="48" r={R} fill="none" stroke="var(--color-border)" strokeWidth="6" />
          {hasData && meta ? (
            <circle
              cx="48"
              cy="48"
              r={R}
              fill="none"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={CIRC}
              strokeDashoffset={dash}
              className={meta.ring}
            />
          ) : null}
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <span className="text-text font-serif text-[30px] font-medium tracking-tight tabular-nums">
            {isLoading ? "—" : (score ?? "—")}
          </span>
        </div>
      </div>
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
          Readiness
        </span>
        {hasData && meta ? (
          <>
            <span className={cn("text-[15px] font-semibold", meta.tone)}>{meta.copy}</span>
            <Link
              href="/health"
              className="text-text-tertiary hover:text-text text-xs transition-colors"
            >
              From your wearable →
            </Link>
          </>
        ) : (
          <span className="text-text-secondary text-[15px] font-medium">Loading…</span>
        )}
      </div>
    </div>
  );
}
