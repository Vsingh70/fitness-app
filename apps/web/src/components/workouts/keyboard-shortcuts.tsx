"use client";

import { useEffect } from "react";

interface ShortcutsProps {
  /** Focus first input of the last exercise card. */
  onAddSet?: () => void;
  /** Open the ExercisePicker. */
  onAddExercise?: () => void;
}

export function KeyboardShortcuts({ onAddSet, onAddExercise }: ShortcutsProps) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const inField =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.isContentEditable;
      if (inField) return;
      if (event.key === "n" || event.key === "N") {
        event.preventDefault();
        onAddSet?.();
      } else if (event.key === "e" || event.key === "E") {
        event.preventDefault();
        onAddExercise?.();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onAddSet, onAddExercise]);
  return null;
}
