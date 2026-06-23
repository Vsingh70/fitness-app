"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { motion } from "motion/react";
import { snappy } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";

interface PressableProps extends ComponentPropsWithoutRef<typeof motion.button> {
  children: ReactNode;
}

/**
 * Press affordance for a button/row. Editorial restraint: hover lifts a single
 * pixel (a quiet elevation cue, NOT a scale pop); tap settles to scale 0.985.
 *
 * Under `prefers-reduced-motion` both transforms are dropped — the element
 * stays put and relies on its own CSS hover/focus styles.
 */
export function Pressable({ children, ...rest }: PressableProps) {
  const { reduced } = useReducedMotionSafe();

  const interaction = reduced
    ? {}
    : {
        whileHover: { y: -1 },
        whileTap: { scale: 0.985 },
      };

  return (
    <motion.button transition={snappy} {...interaction} {...rest}>
      {children}
    </motion.button>
  );
}
