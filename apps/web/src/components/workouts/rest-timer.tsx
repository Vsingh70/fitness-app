"use client";

import { useEffect, useRef, useState } from "react";

import { playTone } from "@/lib/audio/unlock";

interface RestTimerProps {
  /** Total seconds for this rest period. */
  seconds: number;
  /** Called when the timer hits zero (fires once). */
  onComplete?: () => void;
  /** Honor prefers-reduced-motion: skip the spinning ring animation. */
  reducedMotion?: boolean;
  className?: string;
  /** Test seam: inject a clock. Defaults to Date.now. */
  now?: () => number;
}

const RADIUS = 36;
const CIRC = 2 * Math.PI * RADIUS;

export function RestTimer({
  seconds,
  onComplete,
  reducedMotion = false,
  className,
  now = Date.now,
}: RestTimerProps) {
  const startedAtRef = useRef(now());
  const completedRef = useRef(false);
  const [remaining, setRemaining] = useState(seconds);
  const originalTitleRef = useRef<string | null>(null);

  useEffect(() => {
    startedAtRef.current = now();
    completedRef.current = false;
    setRemaining(seconds);
  }, [seconds, now]);

  useEffect(() => {
    const id = window.setInterval(() => {
      const elapsed = (now() - startedAtRef.current) / 1000;
      const left = Math.max(0, seconds - elapsed);
      setRemaining(left);
      if (left <= 0 && !completedRef.current) {
        completedRef.current = true;
        playTone(880, 200);
        if (typeof document !== "undefined") {
          originalTitleRef.current = document.title;
          document.title = "Rest over - " + originalTitleRef.current;
          window.setTimeout(() => {
            if (originalTitleRef.current) document.title = originalTitleRef.current;
          }, 4000);
        }
        onComplete?.();
        window.clearInterval(id);
      }
    }, 100);
    return () => window.clearInterval(id);
  }, [seconds, onComplete, now]);

  const fraction = Math.max(0, Math.min(1, remaining / seconds));
  const dashOffset = CIRC * (1 - fraction);
  const displaySeconds = Math.ceil(remaining);
  return (
    <div className={`relative inline-flex items-center justify-center ${className ?? ""}`}>
      <svg width="88" height="88" viewBox="0 0 88 88" aria-hidden="true">
        <circle
          cx="44"
          cy="44"
          r={RADIUS}
          stroke="var(--color-border)"
          strokeWidth="6"
          fill="none"
        />
        <circle
          cx="44"
          cy="44"
          r={RADIUS}
          stroke="var(--color-accent)"
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={CIRC}
          strokeDashoffset={dashOffset}
          transform="rotate(-90 44 44)"
          style={reducedMotion ? undefined : { transition: "stroke-dashoffset 100ms linear" }}
        />
      </svg>
      <span
        role="timer"
        aria-live="polite"
        className="text-text absolute font-serif text-2xl font-medium tabular-nums"
      >
        {displaySeconds}
      </span>
    </div>
  );
}
