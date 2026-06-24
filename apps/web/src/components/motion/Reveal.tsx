"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { motion } from "motion/react";
import { soft } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";

interface RevealProps extends Omit<ComponentPropsWithoutRef<typeof motion.div>, "children"> {
  children: ReactNode;
  /** Stagger / sequencing delay in seconds. */
  delay?: number;
}

/**
 * Entrance primitive: fades + lifts content in once on mount with the `soft`
 * spring. Under `prefers-reduced-motion` the lift is dropped and it fades only.
 */
export function Reveal({ children, delay = 0, ...rest }: RevealProps) {
  const { safe } = useReducedMotionSafe();
  const variants = safe({
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0 },
  });

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants}
      transition={{ ...soft, delay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
