"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import {
  BLOCK_KIND_LABEL,
  blockCountsAsVolume,
  type BlockKind,
} from "@/lib/workouts/types";

interface BlockGroupProps {
  kind: BlockKind;
  /** Optional free-text label, e.g. "Mobility" (06 §3c). */
  label?: string | null;
  /** Number of exercises in the block, shown in the header. */
  count: number;
  children: ReactNode;
}

/**
 * Visual grouping for a run of exercises sharing a `block_kind` (06 §3c).
 * Warm-up and cooldown blocks render with a dashed, muted frame and a "Not
 * working volume" note so the user can see at a glance that those movements are
 * logged but never counted toward training volume, PRs, or per-muscle analytics.
 * The `working` block renders as a plain header (the default, no chrome).
 */
export function BlockGroup({ kind, label, count, children }: BlockGroupProps) {
  const isVolume = blockCountsAsVolume(kind);

  return (
    <section
      aria-label={`${BLOCK_KIND_LABEL[kind]} block`}
      data-block-kind={kind}
      className={cn(
        "flex flex-col gap-4",
        isVolume
          ? ""
          : "border-border rounded-[var(--radius-card)] border border-dashed bg-[var(--color-surface)]/40 p-3",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "text-[11px] font-semibold tracking-[0.14em] uppercase",
            isVolume ? "text-text-secondary" : "text-text-tertiary",
          )}
        >
          {label?.trim() ? label : BLOCK_KIND_LABEL[kind]}
        </span>
        <span className="text-text-tertiary text-[11px] tabular-nums">
          {count} {count === 1 ? "movement" : "movements"}
        </span>
        {!isVolume ? (
          <span className="border-border text-text-tertiary inline-flex h-[20px] items-center rounded-[var(--radius-pill)] border border-dashed px-2 text-[10px] font-semibold tracking-[0.08em] uppercase">
            Not working volume
          </span>
        ) : null}
      </div>
      {children}
    </section>
  );
}
