"use client";

import { AnimatePresence, motion } from "motion/react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/cn";
import { sheet } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  children: ReactNode;
}

/**
 * Framer-motion bottom-sheet / right-drawer — a drop-in replacement for the Vaul
 * `Sheet` (same `open` / `onOpenChange` / `title` API). The panel springs in (up
 * on mobile, in from the right on desktop) and reverses on exit via
 * `AnimatePresence`; the backdrop fades. Because we drive the animation ourselves
 * we also re-add the dialog behaviours Vaul gave for free: a portal, body
 * scroll-lock, Escape-to-close, focus move-in + restore, and focus containment by
 * marking the rest of the page `inert` while open. Collapses to opacity-only
 * under `prefers-reduced-motion`.
 */
export function Sheet({ open, onOpenChange, title, children }: SheetProps) {
  // Portals need the DOM; defer until mounted so SSR renders nothing.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {open ? (
        <SheetLayer key="sheet" onOpenChange={onOpenChange} title={title}>
          {children}
        </SheetLayer>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}

function SheetLayer({
  onOpenChange,
  title,
  children,
}: {
  onOpenChange: (open: boolean) => void;
  title?: string;
  children: ReactNode;
}) {
  const { safe } = useReducedMotionSafe();
  const overlayRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  // Read the breakpoint synchronously so the first frame slides on the right axis.
  const [isDesktop] = useState(
    () =>
      typeof window !== "undefined" && window.matchMedia?.("(min-width: 768px)").matches === true,
  );

  // Latest onOpenChange read through a ref so the modal effect runs once per open
  // (not on every parent re-render, which would thrash focus + inert).
  const onOpenChangeRef = useRef(onOpenChange);
  onOpenChangeRef.current = onOpenChange;

  // Modal side effects, set up once per open (SheetLayer remounts per open).
  useEffect(() => {
    const body = document.body;
    const prevOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    const previouslyFocused = document.activeElement as HTMLElement | null;

    // Defer focus-move + the inert loop to after the first paint: doing them
    // synchronously here forces a style/layout reflow on the same frame the
    // entrance spring starts, which is what made the open feel choppy.
    const inerted: Element[] = [];
    const raf = requestAnimationFrame(() => {
      const overlay = overlayRef.current;
      if (overlay) {
        for (const child of Array.from(body.children)) {
          if (child !== overlay && !child.hasAttribute("inert")) {
            child.setAttribute("inert", "");
            inerted.push(child);
          }
        }
      }
      const panel = panelRef.current;
      const focusable = panel?.querySelector<HTMLElement>(
        'input, button, textarea, select, a[href], [tabindex]:not([tabindex="-1"])',
      );
      (focusable ?? panel)?.focus();
    });

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      // Only the topmost sheet reacts: ignore Escape when focus is inside a
      // different (nested) dialog, e.g. the still-Vaul create-exercise sheet.
      const owner = document.activeElement?.closest?.('[role="dialog"]');
      if (owner && owner !== panelRef.current) return;
      e.stopPropagation();
      onOpenChangeRef.current(false);
    };
    document.addEventListener("keydown", onKey);

    return () => {
      cancelAnimationFrame(raf);
      body.style.overflow = prevOverflow;
      document.removeEventListener("keydown", onKey);
      for (const child of inerted) child.removeAttribute("inert");
      previouslyFocused?.focus?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const panel = safe({
    hidden: { opacity: 0, ...(isDesktop ? { x: "100%" } : { y: "100%" }) },
    visible: { opacity: 1, x: 0, y: 0 },
  });

  return (
    <motion.div ref={overlayRef} className="fixed inset-0 z-50">
      <motion.div
        className="bg-overlay absolute inset-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <motion.div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cn(
          "bg-surface-elevated border-border fixed right-0 bottom-0 left-0 z-10 mx-auto max-h-[92vh] max-w-2xl overflow-y-auto border p-5 outline-none",
          "rounded-t-[var(--radius-sheet)]",
          "md:inset-y-0 md:right-0 md:left-auto md:mx-0 md:max-h-none md:w-[420px] md:max-w-none md:rounded-t-none md:rounded-l-[var(--radius-sheet)]",
        )}
        variants={panel}
        initial="hidden"
        animate="visible"
        exit="hidden"
        transition={sheet}
        style={{ willChange: "transform, opacity" }}
      >
        <div className="bg-text-tertiary mx-auto mb-4 h-1.5 w-9 rounded-full md:hidden" />
        {title ? (
          <h2 className="text-text mb-4 font-serif text-xl font-medium tracking-tight">{title}</h2>
        ) : null}
        {children}
      </motion.div>
    </motion.div>
  );
}
