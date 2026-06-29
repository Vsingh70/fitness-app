"use client";

import { labelize } from "@/lib/api/exercises";

interface Props {
  name: string;
  trackingType: string;
  onSkipAhead: () => void;
}

export function NextUpPreview({ name, trackingType, onSkipAhead }: Props) {
  return (
    <div className="border-border bg-surface-elevated flex items-center gap-3 rounded-[var(--radius-card)] border px-4 py-3 opacity-90">
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
        Up next
      </span>
      <span className="text-text text-sm font-medium">{name}</span>
      <span className="text-text-tertiary text-xs">· {labelize(trackingType)}</span>
      <button
        type="button"
        onClick={onSkipAhead}
        className="text-text-secondary hover:text-text ml-auto text-[12px] font-semibold tracking-[0.08em] uppercase"
      >
        Skip ahead →
      </button>
    </div>
  );
}
