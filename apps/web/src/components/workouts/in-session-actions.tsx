"use client";

import { AlertTriangle, ChevronRight, Pencil, Repeat, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Sheet } from "@/components/ui/sheet";
import { cn } from "@/lib/cn";
import type { IntensityMode, ProgramDayExercise } from "@/lib/programs/types";
import type { ProgramDayExerciseUpdate } from "@/lib/programs/types";
import { ProgramTargetEditor } from "./program-target-editor";

/** Quiet, non-blocking failure badge (design brief §7 / 05 §6). */
export type SyncState = "idle" | "saving" | "synced" | "error";

interface InSessionActionsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  exerciseName: string;
  /**
   * The matching active-program slot exercise, when the session is program-linked.
   * `null` for freestyle sessions or when this movement isn't in the slot — the
   * program-edit rows hide and only the session-only swap is offered.
   */
  slotExercise: ProgramDayExercise | null;
  intensityMode: IntensityMode;
  /** Per-program-action sync state, surfaced as a quiet inline badge. */
  programSyncState: SyncState;
  /** Open the exercise picker to swap for this session only (05 §2). */
  onSwapForSession: () => void;
  /** Open the exercise picker to swap in the program (05 §3, now + forward). */
  onSwapInProgram: () => void;
  /** Persist edited targets to the active program slot (05 §3). */
  onChangeTargets: (body: ProgramDayExerciseUpdate) => void;
  /** Remove this exercise from the active program slot (05 §3). */
  onRemoveFromProgram: () => void;
  /** Remove this exercise from this session only (leaves the program intact). */
  onRemoveFromSession: () => void;
}

type View = "menu" | "edit";

/**
 * The in-session divergence menu (05). A single bottom sheet (one level deep)
 * offering: swap for this session, change/swap in program, remove from program.
 * Opening the exercise picker from here is the only second sheet, so the stack
 * never exceeds two (05 §6). All program writes report through a quiet badge,
 * never a blocking modal.
 */
export function InSessionActions({
  open,
  onOpenChange,
  exerciseName,
  slotExercise,
  intensityMode,
  programSyncState,
  onSwapForSession,
  onSwapInProgram,
  onChangeTargets,
  onRemoveFromProgram,
  onRemoveFromSession,
}: InSessionActionsProps) {
  const [view, setView] = useState<View>("menu");
  const inProgram = slotExercise !== null;

  const close = () => {
    onOpenChange(false);
    // Reset to the menu after the close animation so it reopens on the root view.
    window.setTimeout(() => setView("menu"), 250);
  };

  return (
    <Sheet
      open={open}
      onOpenChange={(v) => {
        if (!v) close();
        else onOpenChange(true);
      }}
      title={view === "edit" ? `Change ${exerciseName}` : exerciseName}
    >
      {programSyncState === "error" ? (
        <div
          role="status"
          className="border-border text-text-secondary bg-surface mb-3 flex items-center gap-2 rounded-[var(--radius-button)] border px-3 py-2 text-xs"
        >
          <AlertTriangle className="text-destructive h-3.5 w-3.5" aria-hidden />
          Program change didn’t sync. It’ll retry — your logged sets are safe.
        </div>
      ) : null}

      {view === "menu" ? (
        <div className="flex flex-col">
          <ActionRow
            icon={<Repeat className="h-[18px] w-[18px]" />}
            label="Swap for this session"
            hint="Log to a substitute today. The program stays the same."
            onClick={() => {
              onSwapForSession();
              close();
            }}
          />
          {inProgram ? (
            <>
              <ActionRow
                icon={<Pencil className="h-[18px] w-[18px]" />}
                label="Change in program"
                hint="Edit sets, reps, and intensity. Applies now and forward."
                trailing={<ChevronRight className="text-text-tertiary h-4 w-4" />}
                onClick={() => setView("edit")}
              />
              <ActionRow
                icon={<Repeat className="h-[18px] w-[18px]" />}
                label="Swap in program"
                hint="Replace this movement in the program for every cycle."
                onClick={() => {
                  onSwapInProgram();
                  close();
                }}
              />
              <ActionRow
                icon={<Trash2 className="h-[18px] w-[18px]" />}
                label="Remove from program"
                hint="Drop it now and forward. Past history is kept."
                destructive
                onClick={() => {
                  onRemoveFromProgram();
                  close();
                }}
              />
            </>
          ) : (
            <p className="text-text-tertiary px-1 py-3 text-xs">
              This is a freestyle session, so there’s no program slot to change.
            </p>
          )}
          <ActionRow
            icon={<Trash2 className="h-[18px] w-[18px]" />}
            label="Remove from this session"
            hint="Take it off today only. The program is untouched."
            destructive
            onClick={() => {
              onRemoveFromSession();
              close();
            }}
          />
        </div>
      ) : slotExercise ? (
        <ProgramTargetEditor
          pde={slotExercise}
          intensityMode={intensityMode}
          saving={programSyncState === "saving"}
          onSave={(body) => {
            onChangeTargets(body);
            close();
          }}
          onCancel={() => setView("menu")}
        />
      ) : null}
    </Sheet>
  );
}

function ActionRow({
  icon,
  label,
  hint,
  trailing,
  destructive = false,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  hint: string;
  trailing?: ReactNode;
  destructive?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "border-border flex w-full items-center gap-3 border-b py-3 text-left last:border-b-0",
        "hover:bg-surface -mx-1 rounded-[var(--radius-button)] px-1 transition-colors duration-150",
      )}
    >
      <span
        className={cn(
          "grid h-9 w-9 shrink-0 place-items-center rounded-full",
          destructive ? "bg-destructive/10 text-destructive" : "bg-surface text-text-secondary",
        )}
        aria-hidden
      >
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            "block font-serif text-[15px] font-medium",
            destructive ? "text-destructive" : "text-text",
          )}
        >
          {label}
        </span>
        <span className="text-text-tertiary block text-xs">{hint}</span>
      </span>
      {trailing}
    </button>
  );
}
