"use client";

import { useEffect, useState } from "react";

function formatHMS(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}

interface SessionTimerProps {
  startedAtMs: number;
  endedAtMs?: number | null;
  className?: string;
}

export function SessionTimer({ startedAtMs, endedAtMs, className }: SessionTimerProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (endedAtMs) return;
    // 1-second interval is sufficient: the display only shows whole seconds.
    // The rAF loop called setNow ~60×/sec; 59/60 of those were wasted renders.
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    const onVisibility = () => {
      if (document.visibilityState === "visible") setNow(Date.now());
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [endedAtMs]);

  const endMs = endedAtMs ?? now;
  return (
    <span role="timer" aria-live="off" className={`tabular-nums ${className ?? ""}`}>
      {formatHMS((endMs - startedAtMs) / 1000)}
    </span>
  );
}
