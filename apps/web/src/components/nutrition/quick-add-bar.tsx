"use client";

import { Plus, ScanLine } from "lucide-react";

interface Props {
  /** Open the add-meal flow on the Search tab. */
  onAdd: () => void;
  /** Open the add-meal flow on the Scan-barcode tab. */
  onScan: () => void;
}

/**
 * The hero action of the day screen: a tall ink-bordered "search" bar that
 * opens the add-meal flow, with a clay + button and a small Scan affordance.
 */
export function QuickAddBar({ onAdd, onScan }: Props) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={onAdd}
        className="border-text bg-bg text-text-tertiary hover:bg-surface flex h-14 flex-1 items-center justify-between rounded-[var(--radius-button)] border-[1.5px] pr-2 pl-4 text-left transition-colors duration-150 ease-out"
      >
        <span className="font-serif text-[17px]">What did you eat?</span>
        <span className="bg-accent text-accent-foreground grid h-10 w-10 place-items-center rounded-[var(--radius-button)]">
          <Plus className="h-5 w-5" aria-hidden />
        </span>
      </button>
      <button
        type="button"
        onClick={onScan}
        className="border-border-strong text-text-secondary hover:border-text hover:text-text flex h-14 items-center gap-2 rounded-[var(--radius-button)] border px-4 text-[12px] font-semibold tracking-[0.08em] uppercase transition-colors duration-150 ease-out"
      >
        <ScanLine className="h-4 w-4" aria-hidden /> Scan
      </button>
    </div>
  );
}
