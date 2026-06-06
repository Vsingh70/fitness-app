"use client";

import { useEffect } from "react";

interface ShortcutsProps {
  /** Focus first input of the last exercise card. */
  onAddSet?: () => void;
  /** Open the ExercisePicker. */
  onAddExercise?: () => void;
  /** Open the help sheet (also fires on `?`). */
  onShowHelp?: () => void;
  /** Move to the next exercise (j). */
  onNextExercise?: () => void;
  /** Move to the previous exercise (k). */
  onPrevExercise?: () => void;
  /** Toggle the rest timer (r). */
  onToggleRest?: () => void;
}

export function KeyboardShortcuts({
  onAddSet,
  onAddExercise,
  onShowHelp,
  onNextExercise,
  onPrevExercise,
  onToggleRest,
}: ShortcutsProps) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const inField =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;
      if (inField) return;

      if (event.key === "?" || (event.shiftKey && event.key === "/")) {
        event.preventDefault();
        onShowHelp?.();
        return;
      }

      const key = event.key.toLowerCase();
      switch (key) {
        case "n":
          event.preventDefault();
          onAddSet?.();
          break;
        case "e":
          event.preventDefault();
          onAddExercise?.();
          break;
        case "j":
          event.preventDefault();
          onNextExercise?.();
          break;
        case "k":
          event.preventDefault();
          onPrevExercise?.();
          break;
        case "r":
          event.preventDefault();
          onToggleRest?.();
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onAddSet, onAddExercise, onShowHelp, onNextExercise, onPrevExercise, onToggleRest]);
  return null;
}

interface SheetProps {
  open: boolean;
  onClose: () => void;
}

const ROWS: { keys: string[]; description: string }[] = [
  { keys: ["j", "k"], description: "Next / previous exercise" },
  { keys: ["n"], description: "Focus the add-set row" },
  { keys: ["e"], description: "Open exercise picker" },
  { keys: ["r"], description: "Start / skip rest timer" },
  { keys: ["⌘", "↵"], description: "Save the current set" },
  { keys: ["?"], description: "This sheet" },
  { keys: ["Esc"], description: "Close sheets & popovers" },
];

export function KeyboardShortcutsSheet({ open, onClose }: SheetProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="kb-sheet-title"
      className="bg-overlay fixed inset-0 z-50 grid place-items-center p-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-surface-elevated border-border w-full max-w-[480px] rounded-[var(--radius-sheet)] border p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <h3 id="kb-sheet-title" className="font-serif text-xl font-medium tracking-tight">
          Keyboard shortcuts
        </h3>
        <div className="mt-4 flex flex-col">
          {ROWS.map(({ keys, description }) => (
            <div
              key={description}
              className="border-border grid grid-cols-[110px_1fr] gap-3 border-b py-2 text-[13px] last:border-b-0"
            >
              <div className="flex items-center gap-1">
                {keys.map((k, i) => (
                  <span key={`${k}-${i}`}>
                    <kbd className="bg-surface border-border text-text inline-flex h-6 items-center rounded border px-1.5 font-mono text-[11px]">
                      {k}
                    </kbd>
                    {i < keys.length - 1 ? (
                      <span className="text-text-tertiary mx-1 text-[11px]">/</span>
                    ) : null}
                  </span>
                ))}
              </div>
              <span className="text-text-secondary">{description}</span>
            </div>
          ))}
        </div>
        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="text-text-secondary hover:text-text text-[12px] font-semibold tracking-[0.08em] uppercase"
          >
            Got it · Esc
          </button>
        </div>
      </div>
    </div>
  );
}
