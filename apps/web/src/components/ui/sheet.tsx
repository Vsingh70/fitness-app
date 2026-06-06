"use client";

import type { ReactNode } from "react";
import { Drawer } from "vaul";
import { cn } from "@/lib/cn";

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  children: ReactNode;
}

export function Sheet({ open, onOpenChange, title, children }: SheetProps) {
  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange}>
      <Drawer.Portal>
        <Drawer.Overlay className="bg-overlay fixed inset-0 z-40 backdrop-blur-sm" />
        <Drawer.Content
          className={cn(
            "fixed right-0 bottom-0 left-0 z-50 mx-auto max-w-2xl",
            "bg-surface-elevated border-border rounded-t-[var(--radius-sheet)] border p-5",
            "md:inset-y-0 md:right-0 md:left-auto md:w-[420px] md:max-w-none md:rounded-t-none md:rounded-l-[var(--radius-sheet)]",
          )}
        >
          <div className="bg-text-tertiary mx-auto mb-4 h-1.5 w-9 rounded-full md:hidden" />
          {title ? (
            <Drawer.Title className="text-text mb-4 font-serif text-xl font-medium tracking-tight">
              {title}
            </Drawer.Title>
          ) : null}
          {children}
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
