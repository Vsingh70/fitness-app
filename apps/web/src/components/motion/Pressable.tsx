"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cn } from "@/lib/cn";

interface PressableProps extends ComponentPropsWithoutRef<"button"> {
  children: ReactNode;
}

/**
 * Press affordance for a button/row. Editorial restraint: hover lifts a single
 * pixel (a quiet elevation cue, NOT a scale pop); tap settles to scale 0.985.
 *
 * The hover lift and tap settle are pure CSS (GPU-composited transforms,
 * transitioned smoothly) — cheap, with no per-button JS motion. Under
 * `prefers-reduced-motion` both transforms are dropped via the `motion-reduce:`
 * variants and the element relies on its own CSS hover/focus styles.
 */
export function Pressable({ children, className, ...rest }: PressableProps) {
  return (
    <button
      className={cn(
        "transition-transform duration-150 ease-out hover:-translate-y-px active:scale-[0.985] motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
