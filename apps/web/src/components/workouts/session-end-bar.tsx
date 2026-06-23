"use client";

import { Flag, SkipForward } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";

interface SessionEndBarProps {
  finishing: boolean;
  skipping: boolean;
  onFinish: () => void;
  onSkip: () => void;
}

/**
 * Bottom-left, one-handed reach (05 §6): finishing and skipping must sit in the
 * lower portion of the screen during a session, not only the masthead. A single
 * pill opens a short sheet (one level deep) with Finish and Skip. The skip ends
 * the session as skipped — the rotation advances neutrally (05 §4) — and never
 * blocks: a failed sync is handled upstream as a quiet badge, not a modal here.
 */
export function SessionEndBar({ finishing, skipping, onFinish, onSkip }: SessionEndBarProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className="fixed bottom-24 left-4 z-30 sm:bottom-4 md:bottom-6 md:left-6">
      <button
        type="button"
        onClick={() => setOpen(true)}
        data-testid="session-end-bar"
        className="bg-surface-elevated border-border text-text-secondary hover:text-text inline-flex h-[44px] items-center gap-2 rounded-[var(--radius-pill)] border px-4 text-[11px] font-semibold tracking-[0.1em] uppercase shadow-[var(--shadow-2)]"
      >
        <Flag className="h-4 w-4" aria-hidden />
        End
      </button>

      <Sheet open={open} onOpenChange={setOpen} title="End this workout">
        <div className="flex flex-col gap-3">
          <p className="text-text-tertiary text-sm">
            Finishing runs PR detection and routes to the summary. Skipping keeps any sets you
            logged, marks the workout skipped, and advances your program neutrally — no stall.
          </p>
          <Button
            type="button"
            disabled={finishing}
            data-testid="finish-workout-sheet"
            onClick={() => {
              onFinish();
              setOpen(false);
            }}
          >
            <Flag className="h-4 w-4" aria-hidden />
            {finishing ? "Finishing…" : "Finish workout"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={skipping}
            data-testid="skip-workout-sheet"
            onClick={() => {
              onSkip();
              setOpen(false);
            }}
          >
            <SkipForward className="h-4 w-4" aria-hidden />
            {skipping ? "Skipping…" : "Skip workout"}
          </Button>
        </div>
      </Sheet>
    </div>
  );
}
