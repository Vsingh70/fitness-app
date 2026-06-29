"use client";

import { ChevronDown } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useRef, useState } from "react";

import { snappy } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";

/** Format seconds as M:SS (e.g. 90 -> "1:30"). */
export function secondsToLabel(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

// None, then 0:15 → 10:00 in 15-second steps.
const REST_OPTIONS: (number | null)[] = [
  null,
  ...Array.from({ length: 40 }, (_, i) => (i + 1) * 15),
];

/**
 * Styled rest-time dropdown: fixed 15-second steps (None + 0:15 → 10:00). The
 * menu animates open/close (snappy, reduced-motion-safe), closes on outside
 * click / Escape / select, and scrolls the current value into view on open.
 */
export function RestPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (seconds: number | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const { reduced } = useReducedMotionSafe();
  const rootRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<HTMLButtonElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    // optional-call: jsdom doesn't implement scrollIntoView.
    selectedRef.current?.scrollIntoView?.({ block: "nearest" });
    const onDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const label = value == null ? "None" : secondsToLabel(value);

  return (
    <div className="ew-rest" ref={rootRef}>
      <button
        type="button"
        className="ew-rest-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{label}</span>
        <ChevronDown size={13} aria-hidden />
      </button>
      <AnimatePresence>
        {open ? (
          <motion.div
            id={listId}
            role="listbox"
            aria-label="Rest time"
            className="ew-rest-menu"
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: -4, scale: 0.98 }}
            animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: -4, scale: 0.98 }}
            transition={snappy}
            style={{ transformOrigin: "top" }}
          >
            {REST_OPTIONS.map((opt) => {
              const selected = opt === value || (opt == null && value == null);
              return (
                <button
                  key={opt ?? "none"}
                  ref={selected ? selectedRef : undefined}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={selected ? "ew-rest-opt on" : "ew-rest-opt"}
                  onClick={() => {
                    onChange(opt);
                    setOpen(false);
                  }}
                >
                  {opt == null ? "None" : secondsToLabel(opt)}
                </button>
              );
            })}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
