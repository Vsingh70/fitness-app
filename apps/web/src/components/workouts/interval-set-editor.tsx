"use client";

import { Minus, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import { type SetCreate, type SetSegmentCreate } from "@/lib/workouts/types";
import { IntervalTimer } from "./interval-timer";

interface IntervalSetEditorProps {
  /** Commit the interval set: `set_type=interval`, `rounds`, work/rest segments. */
  onSubmit: (payload: SetCreate) => void | Promise<void>;
  onCancel?: () => void;
}

const MIN_ROUNDS = 1;
const MAX_ROUNDS = 50;

function clampRounds(n: number): number {
  return Math.min(MAX_ROUNDS, Math.max(MIN_ROUNDS, n));
}

/**
 * Configure and run an interval / HIIT set (06 §3b). The user sets a round count
 * and one round's work/rest seconds; the embedded interval timer drives the
 * work→rest countdown across all rounds. Logging stores `rounds` plus a `work`
 * and (optional) `rest` segment describing one round.
 */
export function IntervalSetEditor({ onSubmit, onCancel }: IntervalSetEditorProps) {
  const { reduced } = useReducedMotionSafe();
  const [rounds, setRounds] = useState(8);
  const [work, setWork] = useState("30");
  const [rest, setRest] = useState("15");
  const [error, setError] = useState<string | null>(null);

  const workSeconds = useMemo(() => Number.parseInt(work, 10) || 0, [work]);
  const restSeconds = useMemo(() => Number.parseInt(rest, 10) || 0, [rest]);
  const valid = rounds >= MIN_ROUNDS && workSeconds > 0;

  const commit = async () => {
    if (!valid) {
      setError("An interval set needs at least one round and a work duration.");
      return;
    }
    setError(null);
    const segments: SetSegmentCreate[] = [
      { kind: "work", segment_index: 0, duration_seconds: workSeconds },
    ];
    if (restSeconds > 0) {
      segments.push({ kind: "rest", segment_index: 1, duration_seconds: restSeconds });
    }
    const payload: SetCreate = {
      set_type: "interval",
      rounds,
      duration_seconds: workSeconds * rounds,
      segments,
    };
    await onSubmit(payload);
  };

  return (
    <div
      data-testid="interval-set-editor"
      className="border-border bg-surface flex flex-col gap-3 rounded-[var(--radius-card)] border p-3"
    >
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.12em] uppercase">
        Interval set
      </span>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
            Rounds
          </span>
          <div className="flex items-center gap-1.5">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              aria-label="Fewer rounds"
              disabled={rounds <= MIN_ROUNDS}
              onClick={() => setRounds((r) => clampRounds(r - 1))}
            >
              <Minus className="h-4 w-4" />
            </Button>
            <span className="text-text w-[2.5rem] text-center font-serif text-[17px] font-medium tabular-nums">
              {rounds}
            </span>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              aria-label="More rounds"
              disabled={rounds >= MAX_ROUNDS}
              onClick={() => setRounds((r) => clampRounds(r + 1))}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <label className="flex flex-col gap-1">
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
            Work s
          </span>
          <Input
            inputMode="numeric"
            aria-label="Work seconds"
            value={work}
            onChange={(e) => {
              setWork(e.target.value);
              setError(null);
            }}
            className="h-9 w-[5rem] text-right font-serif font-medium tabular-nums"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
            Rest s
          </span>
          <Input
            inputMode="numeric"
            aria-label="Rest seconds"
            value={rest}
            onChange={(e) => {
              setRest(e.target.value);
              setError(null);
            }}
            className="h-9 w-[5rem] text-right font-serif font-medium tabular-nums"
          />
        </label>
      </div>

      {valid ? (
        <IntervalTimer
          rounds={rounds}
          workSeconds={workSeconds}
          restSeconds={restSeconds}
          reducedMotion={reduced}
        />
      ) : null}

      {error ? (
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Button type="button" size="sm" onClick={() => void commit()} disabled={!valid}>
          Log interval set
        </Button>
        {onCancel ? (
          <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  );
}
