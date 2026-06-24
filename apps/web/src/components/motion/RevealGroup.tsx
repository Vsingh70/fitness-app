"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { motion } from "motion/react";
import { soft } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";

const STAGGER = 0.05;

type DivProps = Omit<ComponentPropsWithoutRef<typeof motion.div>, "children">;

interface RevealGroupProps extends DivProps {
  children: ReactNode;
  /** Per-child stagger in seconds. */
  stagger?: number;
  /** Delay before the first child reveals. */
  delay?: number;
}

/**
 * Orchestrates a one-shot, page-load reveal: staggers its `<RevealItem>`
 * children by `stagger` seconds (0.05 default). The single high-impact reveal
 * moment for a surface — not scattered micro-animations.
 *
 * Under reduced motion the children fade only (no lift), still staggered.
 */
export function RevealGroup({
  children,
  stagger = STAGGER,
  delay = 0,
  ...rest
}: RevealGroupProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: { staggerChildren: stagger, delayChildren: delay },
        },
      }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

interface RevealItemProps extends Omit<ComponentPropsWithoutRef<typeof motion.div>, "children"> {
  children: ReactNode;
}

/**
 * A child of `<RevealGroup>`. Inherits the parent's stagger orchestration via
 * the shared `hidden`/`visible` variant names.
 */
export function RevealItem({ children, ...rest }: RevealItemProps) {
  const { safe } = useReducedMotionSafe();
  const variants = safe({
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0 },
  });

  return (
    <motion.div variants={variants} transition={soft} {...rest}>
      {children}
    </motion.div>
  );
}
