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
        <Drawer.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm" />
        <Drawer.Content
          className={cn(
            "fixed bottom-0 left-0 right-0 z-50 mx-auto max-w-2xl",
            "rounded-t-[var(--radius-sheet)] bg-surface-elevated p-4",
            "md:inset-y-0 md:left-auto md:right-0 md:w-[420px] md:max-w-none md:rounded-l-[var(--radius-sheet)] md:rounded-t-none",
          )}
        >
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border md:hidden" />
          {title ? (
            <Drawer.Title className="mb-3 text-lg font-semibold text-text">{title}</Drawer.Title>
          ) : null}
          {children}
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
