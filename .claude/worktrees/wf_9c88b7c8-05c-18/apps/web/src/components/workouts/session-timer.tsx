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
    let raf = 0;
    let cancelled = false;
    const tick = () => {
      if (cancelled) return;
      setNow(Date.now());
      raf = window.requestAnimationFrame(tick);
    };
    raf = window.requestAnimationFrame(tick);
    const onVisibility = () => {
      if (document.visibilityState === "visible") setNow(Date.now());
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(raf);
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
