"use client";

import { useEffect } from "react";
import { create } from "zustand";
import { cn } from "@/lib/cn";

type ToastKind = "info" | "success" | "warning" | "error";

interface ToastItem {
  id: string;
  kind: ToastKind;
  message: string;
}

interface ToastStore {
  items: ToastItem[];
  push: (toast: Omit<ToastItem, "id">) => void;
  dismiss: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  items: [],
  push: (toast) =>
    set((state) => ({
      items: [...state.items, { ...toast, id: crypto.randomUUID() }],
    })),
  dismiss: (id) =>
    set((state) => ({
      items: state.items.filter((t) => t.id !== id),
    })),
}));

const KIND_CLASSES: Record<ToastKind, string> = {
  info: "border-border bg-surface-elevated text-text",
  success: "border-success/40 bg-success/10 text-text",
  warning: "border-warning/40 bg-warning/10 text-text",
  error: "border-destructive/40 bg-destructive/10 text-text",
};

export function ToastViewport() {
  const items = useToastStore((s) => s.items);
  const dismiss = useToastStore((s) => s.dismiss);

  useEffect(() => {
    if (items.length === 0) return;
    const handle = window.setTimeout(() => dismiss(items[0]!.id), 3500);
    return () => window.clearTimeout(handle);
  }, [items, dismiss]);

  return (
    <div className="pointer-events-none fixed top-4 right-4 z-50 flex flex-col gap-2">
      {items.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "pointer-events-auto rounded-[var(--radius-button)] border px-4 py-2 shadow-md",
            KIND_CLASSES[toast.kind],
          )}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}
