"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { sheet } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import { cn } from "@/lib/cn";

interface SheetProps extends Omit<ComponentPropsWithoutRef<typeof motion.div>, "children"> {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Extra classes for the content panel. */
  className?: string;
  /** Extra classes for the backdrop. */
  backdropClassName?: string;
}

/**
 * Motion-driven sheet / dialog content. The backdrop fades; the panel springs
 * in from `{opacity:0, y:12}` and reverses on exit, mounted/unmounted via
 * `AnimatePresence`. Under `prefers-reduced-motion` the panel fades only.
 *
 * State is controlled by the caller (`open` / `onClose`). This is the motion
 * primitive; it does not own a portal, focus trap, or DOM structure beyond the
 * backdrop + panel — compose those at the call site as needed.
 */
export function Sheet({
  open,
  onClose,
  children,
  className,
  backdropClassName,
  ...rest
}: SheetProps) {
  const { safe } = useReducedMotionSafe();
  const panel = safe({
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0 },
  });

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
          initial="hidden"
          animate="visible"
          exit="hidden"
        >
          <motion.div
            className={cn("bg-overlay absolute inset-0", backdropClassName)}
            variants={{ hidden: { opacity: 0 }, visible: { opacity: 1 } }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            className={cn(
              "bg-surface-elevated border-border relative z-10 w-full max-w-md border",
              "rounded-t-[var(--radius-sheet)] p-5 sm:rounded-[var(--radius-sheet)]",
              className,
            )}
            role="dialog"
            aria-modal="true"
            variants={panel}
            transition={sheet}
            {...rest}
          >
            {children}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
