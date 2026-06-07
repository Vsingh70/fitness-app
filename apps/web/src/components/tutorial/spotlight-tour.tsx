"use client";

import { useCallback, useEffect, useLayoutEffect, useState } from "react";

import { cn } from "@/lib/cn";
import { useTutorialStore } from "@/lib/hooks/use-tutorial";

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PAD = 8; // spotlight padding around the target
const BUBBLE_W = 300;
const BUBBLE_GAP = 14;

function measure(target: string | null): Rect | null {
  if (target === null || typeof document === "undefined") return null;
  // Prefer a visible match (sidebar on desktop, tab bar on mobile both share the id).
  const nodes = Array.from(document.querySelectorAll<HTMLElement>(`[data-tutorial="${target}"]`));
  const visible = nodes.find((n) => {
    const r = n.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });
  if (!visible) return null;
  const r = visible.getBoundingClientRect();
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

export function SpotlightTour() {
  const running = useTutorialStore((s) => s.running);
  const finish = useTutorialStore((s) => s.finish);
  const steps = useTutorialStore((s) => s.steps);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);

  const step = steps[index];
  const isFirst = index === 0;
  const isLast = index === steps.length - 1;

  const remeasure = useCallback(() => {
    setRect(measure(step?.target ?? null));
  }, [step?.target]);

  // Reset to the first step whenever the tour (re)starts.
  useEffect(() => {
    if (running) setIndex(0);
  }, [running]);

  // Measure the spotlight target for the current step, and keep it in sync with
  // layout changes (scroll, resize). useLayoutEffect avoids a one-frame flash.
  useLayoutEffect(() => {
    if (!running) return;
    remeasure();
    const onChange = () => remeasure();
    window.addEventListener("resize", onChange);
    window.addEventListener("scroll", onChange, true);
    // A short retry in case the target mounts a tick later (e.g. nav hydration).
    const t = window.setTimeout(remeasure, 60);
    return () => {
      window.removeEventListener("resize", onChange);
      window.removeEventListener("scroll", onChange, true);
      window.clearTimeout(t);
    };
  }, [running, remeasure]);

  // Keyboard: Esc skips, arrows navigate.
  useEffect(() => {
    if (!running) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") finish();
      else if (e.key === "ArrowRight" || e.key === "Enter") {
        if (isLast) finish();
        else setIndex((i) => Math.min(i + 1, steps.length - 1));
      } else if (e.key === "ArrowLeft") {
        setIndex((i) => Math.max(i - 1, 0));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [running, isLast, finish, steps.length]);

  if (!running || !step) return null;

  const next = () => (isLast ? finish() : setIndex((i) => i + 1));
  const back = () => setIndex((i) => Math.max(i - 1, 0));

  // Position the bubble: centered when there's no target, otherwise near the
  // spotlight (below it, or above if it'd overflow the viewport bottom).
  const vw = typeof window !== "undefined" ? window.innerWidth : 1024;
  const vh = typeof window !== "undefined" ? window.innerHeight : 768;

  let bubbleStyle: React.CSSProperties;
  if (!rect) {
    bubbleStyle = {
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: Math.min(BUBBLE_W, vw - 32),
    };
  } else {
    const below = rect.top + rect.height + BUBBLE_GAP;
    const placeAbove = below + 180 > vh && rect.top - 180 > 0;
    const top = placeAbove ? Math.max(16, rect.top - 180) : below;
    let left = rect.left;
    // keep bubble within the viewport horizontally
    left = Math.min(Math.max(16, left), vw - Math.min(BUBBLE_W, vw - 32) - 16);
    bubbleStyle = { top, left, width: Math.min(BUBBLE_W, vw - 32) };
  }

  return (
    <div
      className="fixed inset-0 z-[60]"
      role="dialog"
      aria-modal="true"
      aria-label="Onboarding tour"
    >
      {/* Dim overlay with a cut-out spotlight. We use 4 panels around the rect so
          the highlighted element stays fully interactive-looking and crisp. */}
      {rect ? (
        <>
          {/* top */}
          <div
            className="bg-overlay fixed top-0 right-0 left-0 backdrop-blur-[2px]"
            style={{ height: Math.max(0, rect.top - PAD) }}
            onClick={finish}
          />
          {/* bottom */}
          <div
            className="bg-overlay fixed right-0 bottom-0 left-0 backdrop-blur-[2px]"
            style={{ top: rect.top + rect.height + PAD }}
            onClick={finish}
          />
          {/* left */}
          <div
            className="bg-overlay fixed left-0 backdrop-blur-[2px]"
            style={{
              top: rect.top - PAD,
              height: rect.height + PAD * 2,
              width: Math.max(0, rect.left - PAD),
            }}
            onClick={finish}
          />
          {/* right */}
          <div
            className="bg-overlay fixed right-0 backdrop-blur-[2px]"
            style={{
              top: rect.top - PAD,
              height: rect.height + PAD * 2,
              left: rect.left + rect.width + PAD,
            }}
            onClick={finish}
          />
          {/* highlight ring */}
          <div
            className="border-accent pointer-events-none fixed rounded-[10px] border-2"
            style={{
              top: rect.top - PAD,
              left: rect.left - PAD,
              width: rect.width + PAD * 2,
              height: rect.height + PAD * 2,
            }}
          />
        </>
      ) : (
        <div className="bg-overlay fixed inset-0 backdrop-blur-[2px]" onClick={finish} />
      )}

      {/* Tooltip / step card */}
      <div
        className={cn(
          "bg-surface-elevated border-border fixed flex flex-col gap-3 rounded-[var(--radius-sheet)] border p-4",
          "shadow-[var(--shadow-3)]",
        )}
        style={bubbleStyle}
      >
        <div className="flex items-center justify-between">
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
            Step {index + 1} of {steps.length}
          </span>
          <button
            type="button"
            onClick={finish}
            className="text-text-tertiary hover:text-text text-xs font-medium"
          >
            Skip
          </button>
        </div>

        <div>
          <h3 className="text-text font-serif text-[19px] font-medium tracking-tight">
            {step.title}
          </h3>
          <p className="text-text-secondary mt-1 text-sm leading-snug whitespace-pre-line">
            {step.body}
          </p>
        </div>

        {/* progress dots */}
        <div className="flex items-center gap-1.5" aria-hidden>
          {steps.map((_, i) => (
            <span
              key={i}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === index ? "bg-accent w-4" : "bg-border-strong w-1.5",
              )}
            />
          ))}
        </div>

        <div className="mt-1 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={back}
            disabled={isFirst}
            className="text-text-secondary hover:text-text rounded-[var(--radius-button)] px-2 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-40"
          >
            Back
          </button>
          <button
            type="button"
            onClick={next}
            className="bg-accent text-accent-foreground rounded-[var(--radius-button)] px-4 py-1.5 text-sm font-semibold"
          >
            {isLast ? "Finish" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
