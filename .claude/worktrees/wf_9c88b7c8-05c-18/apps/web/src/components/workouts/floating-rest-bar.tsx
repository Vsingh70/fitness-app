"use client";

import { Clock } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { playTone } from "@/lib/audio/unlock";

interface Props {
  /** When non-null, a rest is active. The number is the total rest seconds. */
  activeKey: number | null;
  /** Total rest seconds for the current period. */
  totalSeconds: number;
  /** Default rest seconds shown in the idle copy. */
  defaultSeconds: number;
  /** Manually start a rest from the bar (idle → active). */
  onStart: () => void;
  /** Skip / cancel the active rest. */
  onSkip: () => void;
}

function mmss(total: number): string {
  const s = Math.max(0, Math.floor(total));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

const RADIUS = 22;
const CIRC = 2 * Math.PI * RADIUS;

export function FloatingRestBar({
  activeKey,
  totalSeconds,
  defaultSeconds,
  onStart,
  onSkip,
}: Props) {
  const startedAtRef = useRef<number>(Date.now());
  const completedRef = useRef(false);
  const [effectiveTotal, setEffectiveTotal] = useState(totalSeconds);
  const [remaining, setRemaining] = useState(totalSeconds);

  useEffect(() => {
    if (activeKey === null) return;
    startedAtRef.current = activeKey;
    completedRef.current = false;
    setEffectiveTotal(totalSeconds);
    setRemaining(totalSeconds);
  }, [activeKey, totalSeconds]);

  useEffect(() => {
    if (activeKey === null) return;
    const id = window.setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000;
      const left = Math.max(0, effectiveTotal - elapsed);
      setRemaining(left);
      if (left <= 0 && !completedRef.current) {
        completedRef.current = true;
        playTone(880, 200);
        window.clearInterval(id);
      }
    }, 200);
    return () => window.clearInterval(id);
  }, [activeKey, effectiveTotal]);

  const extend = () => {
    setEffectiveTotal((t) => t + 30);
    completedRef.current = false;
  };

  const isActive = activeKey !== null && remaining > 0;
  const fraction = isActive ? remaining / effectiveTotal : 0;
  const dash = CIRC * (1 - fraction);
  const display = isActive ? Math.ceil(remaining) : 0;

  return (
    <div
      role="region"
      aria-label="Rest timer"
      className="fixed bottom-4 left-1/2 z-30 -translate-x-1/2 px-4 md:bottom-6"
    >
      <div className="bg-surface-elevated border-border flex items-center gap-4 rounded-[var(--radius-sheet)] border px-4 py-3 shadow-[var(--shadow-3)] md:px-5">
        <div className="relative grid h-[52px] w-[52px] place-items-center">
          {isActive ? (
            <>
              <svg width="52" height="52" viewBox="0 0 52 52" className="-rotate-90">
                <circle
                  cx="26"
                  cy="26"
                  r={RADIUS}
                  fill="none"
                  stroke="var(--color-border)"
                  strokeWidth="4"
                />
                <circle
                  cx="26"
                  cy="26"
                  r={RADIUS}
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={CIRC}
                  strokeDashoffset={dash}
                  style={{ transition: "stroke-dashoffset 200ms linear" }}
                />
              </svg>
              <span
                role="timer"
                aria-live="polite"
                className="text-text font-serif absolute text-[15px] font-medium tabular-nums"
              >
                {display}
              </span>
            </>
          ) : (
            <Clock className="text-text-tertiary h-5 w-5" aria-hidden />
          )}
        </div>
        <div className="flex min-w-0 flex-col">
          <span className="text-text text-[13px] font-semibold uppercase tracking-[0.08em]">
            {isActive ? "Resting" : "No rest"}
          </span>
          <span className="text-text-tertiary text-[12px]">
            {isActive
              ? `${mmss(remaining)} of ${mmss(effectiveTotal)}`
              : `Default ${mmss(defaultSeconds)}`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isActive ? (
            <>
              <Button type="button" variant="ghost" size="sm" onClick={extend}>
                +30s
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={onSkip}>
                Skip
              </Button>
            </>
          ) : (
            <Button type="button" size="sm" onClick={onStart}>
              Start rest
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
