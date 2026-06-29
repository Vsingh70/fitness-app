"use client";

import { motion } from "motion/react";
import { useId } from "react";

import { snappy } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";

/**
 * Compact ink-filled segmented control — the design's `.mini-seg`. Used for the
 * per-exercise Range/Target rep toggle, the program-wide RPE/RIR/Off intensity
 * control, and periodization. The active background is a shared-layout `motion`
 * "pill" that slides between options (per-instance `layoutId`); under
 * `prefers-reduced-motion` it jumps instantly. Styled by programs.css (.mini-seg),
 * not Tailwind, so it matches the prototype. (Distinct from `components/ui/segmented.tsx`.)
 */
export function MiniSegmented<T extends string>({
  options,
  value,
  onChange,
  disabled,
  ariaLabel,
}: {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange?: (value: T) => void;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  const pillId = useId();
  const { reduced } = useReducedMotionSafe();
  return (
    <div className="mini-seg" role="radiogroup" aria-label={ariaLabel}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange?.(opt.value)}
            className={`ms ${active ? "on" : ""}`}
          >
            {active ? (
              <motion.span
                layoutId={`${pillId}-pill`}
                className="mini-seg-pill"
                transition={reduced ? { duration: 0 } : snappy}
                aria-hidden
              />
            ) : null}
            <span className="lbl">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
