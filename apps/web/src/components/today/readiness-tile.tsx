"use client";

import { cn } from "@/lib/cn";
import type { components } from "@/lib/api/types";

type Readiness = components["schemas"]["ReadinessTodayResponse"];

interface Props {
  data: Readiness | undefined;
  isLoading: boolean;
}

const BAND_COPY: Record<
  NonNullable<Readiness["band"]>,
  { copy: string; tone: string; ring: string }
> = {
  high: { copy: "Push it", tone: "text-success", ring: "stroke-[var(--color-success)]" },
  moderate: { copy: "Workable", tone: "text-warning", ring: "stroke-[var(--color-warning)]" },
  low: {
    copy: "Take it easy",
    tone: "text-destructive",
    ring: "stroke-[var(--color-destructive)]",
  },
};

const R = 40;
const CIRC = 2 * Math.PI * R;

export function ReadinessTile({ data, isLoading }: Props) {
  const score = data?.score ?? null;
  const band = data?.band ?? null;
  const hasData = data?.has_data ?? false;
  const fraction = score !== null ? Math.max(0, Math.min(1, score / 100)) : 0;
  const dash = CIRC * (1 - fraction);
  const meta = band ? BAND_COPY[band] : null;

  return (
    <div className="border-border bg-surface-elevated flex items-center gap-5 rounded-[var(--radius-card)] border p-5">
      <div className="relative h-[96px] w-[96px] shrink-0">
        <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
          <circle cx="48" cy="48" r={R} fill="none" stroke="var(--color-border)" strokeWidth="6" />
          {hasData && score !== null && meta ? (
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
            {isLoading ? "—" : score !== null ? score : "—"}
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
            <span className="text-text-tertiary text-xs">Pulled from Fitbit overnight</span>
          </>
        ) : (
          <>
            <span className="text-text-secondary text-[15px] font-medium">No data yet</span>
            <span className="text-text-tertiary text-xs">Connect Fitbit in Settings</span>
          </>
        )}
      </div>
    </div>
  );
}
