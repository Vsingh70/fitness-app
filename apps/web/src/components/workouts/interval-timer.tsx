"use client";

import { Pause, Play, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { playTone } from "@/lib/audio/unlock";
import { cn } from "@/lib/cn";

interface IntervalTimerProps {
  /** Number of rounds (each round = one work phase then one rest phase). */
  rounds: number;
  /** Work phase length, seconds. */
  workSeconds: number;
  /** Rest phase length, seconds. 0 omits the rest phase. */
  restSeconds: number;
  /** Honor prefers-reduced-motion: drop the ring transition. */
  reducedMotion?: boolean;
  /** Fired once when the final round's rest (or work) completes. */
  onComplete?: () => void;
  /** Test seam: inject a clock. Defaults to Date.now. */
  now?: () => number;
}

type Phase = "work" | "rest";

const RADIUS = 30;
const CIRC = 2 * Math.PI * RADIUS;

/**
 * Drives the work/rest countdown across an interval set's rounds (06 §3b). One
 * concept replaces logging each interval as a disconnected `time_only` row: this
 * counts down work → rest → work … advancing the round, and beeps on each phase
 * change so the user never watches the screen.
 */
export function IntervalTimer({
  rounds,
  workSeconds,
  restSeconds,
  reducedMotion = false,
  onComplete,
  now = Date.now,
}: IntervalTimerProps) {
  const [running, setRunning] = useState(false);
  const [round, setRound] = useState(1);
  const [phase, setPhase] = useState<Phase>("work");
  const [remaining, setRemaining] = useState(workSeconds);
  const [done, setDone] = useState(false);

  const startedAtRef = useRef(now());
  const phaseLenRef = useRef(workSeconds);
  // Mutable mirror of the schedule so the interval callback reads live values.
  const stateRef = useRef({ round: 1, phase: "work" as Phase });

  const phaseLength = useCallback(
    (p: Phase) => (p === "work" ? workSeconds : restSeconds),
    [workSeconds, restSeconds],
  );

  const reset = useCallback(() => {
    setRunning(false);
    setRound(1);
    setPhase("work");
    setRemaining(workSeconds);
    setDone(false);
    stateRef.current = { round: 1, phase: "work" };
    phaseLenRef.current = workSeconds;
  }, [workSeconds]);

  // Re-seed when the schedule itself changes (e.g. user edits rounds/work/rest).
  useEffect(() => {
    reset();
  }, [reset, rounds, restSeconds]);

  const beginPhase = useCallback(
    (nextRound: number, nextPhase: Phase) => {
      stateRef.current = { round: nextRound, phase: nextPhase };
      const len = phaseLength(nextPhase);
      phaseLenRef.current = len;
      startedAtRef.current = now();
      setRound(nextRound);
      setPhase(nextPhase);
      setRemaining(len);
    },
    [now, phaseLength],
  );

  const advance = useCallback(() => {
    const { round: r, phase: p } = stateRef.current;
    playTone(p === "work" ? 660 : 880, 180);
    if (p === "work" && restSeconds > 0) {
      beginPhase(r, "rest");
      return;
    }
    // End of a round (work with no rest, or rest finished).
    if (r >= rounds) {
      setRunning(false);
      setDone(true);
      setRemaining(0);
      onComplete?.();
      return;
    }
    beginPhase(r + 1, "work");
  }, [beginPhase, onComplete, restSeconds, rounds]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      const elapsed = (now() - startedAtRef.current) / 1000;
      const left = Math.max(0, phaseLenRef.current - elapsed);
      setRemaining(left);
      if (left <= 0) advance();
    }, 100);
    return () => window.clearInterval(id);
  }, [running, advance, now]);

  const toggle = () => {
    if (done) {
      reset();
      return;
    }
    if (!running) {
      // Resume from where we are without losing elapsed precision.
      startedAtRef.current = now() - (phaseLenRef.current - remaining) * 1000;
      setRunning(true);
    } else {
      setRunning(false);
    }
  };

  const len = phaseLenRef.current || 1;
  const fraction = Math.max(0, Math.min(1, remaining / len));
  const dashOffset = CIRC * (1 - fraction);
  const display = done ? "Done" : Math.ceil(remaining);
  const ringColor = phase === "work" ? "var(--color-accent)" : "var(--color-border-strong)";

  return (
    <div
      data-testid="interval-timer"
      className="border-border bg-surface flex items-center gap-4 rounded-[var(--radius-card)] border p-3"
    >
      <div className="relative grid h-[72px] w-[72px] place-items-center">
        <svg width="72" height="72" viewBox="0 0 72 72" aria-hidden="true">
          <circle cx="36" cy="36" r={RADIUS} stroke="var(--color-border)" strokeWidth="5" fill="none" />
          <circle
            cx="36"
            cy="36"
            r={RADIUS}
            stroke={ringColor}
            strokeWidth="5"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={dashOffset}
            transform="rotate(-90 36 36)"
            style={reducedMotion ? undefined : { transition: "stroke-dashoffset 100ms linear" }}
          />
        </svg>
        <span
          role="timer"
          aria-live="polite"
          className="text-text absolute font-serif text-xl font-medium tabular-nums"
        >
          {display}
        </span>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <span
          className={cn(
            "text-[12px] font-semibold tracking-[0.1em] uppercase",
            done ? "text-success" : phase === "work" ? "text-accent" : "text-text-secondary",
          )}
        >
          {done ? "Intervals complete" : phase === "work" ? "Work" : "Rest"}
        </span>
        <span className="text-text-tertiary text-[12px] tabular-nums">
          Round {Math.min(round, rounds)} / {rounds} · {workSeconds}s work
          {restSeconds > 0 ? ` · ${restSeconds}s rest` : ""}
        </span>
      </div>

      <div className="flex items-center gap-1">
        <Button
          type="button"
          size="sm"
          onClick={toggle}
          aria-label={done ? "Restart intervals" : running ? "Pause intervals" : "Start intervals"}
        >
          {done ? (
            <RotateCcw className="h-4 w-4" />
          ) : running ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>
        {!done ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={reset}
            aria-label="Reset intervals"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        ) : null}
      </div>
    </div>
  );
}
