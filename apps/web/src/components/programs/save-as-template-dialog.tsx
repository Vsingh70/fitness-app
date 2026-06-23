"use client";

import { useEffect, useId, useState } from "react";

import { Sheet } from "@/components/motion/Sheet";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useSaveAsTemplate } from "@/lib/hooks/programs";
import type { TemplateVisibility } from "@/lib/programs/types";

interface SaveAsTemplateDialogProps {
  programId: string;
  /** Pre-fill the name field (the program's own name + " template"). */
  defaultName: string;
  open: boolean;
  onClose: () => void;
}

/**
 * "Save as template" dialog (`.sat-*`): a name field and a Private/Shared
 * visibility choice, posting to `POST /programs/{id}/save-as-template`. The
 * program itself is unchanged; the new template surfaces in Browse templates.
 *
 * Rendered through the `Sheet` motion primitive (AnimatePresence + spring,
 * reduced-motion safe). State is owned by the caller (`open` / `onClose`).
 */
export function SaveAsTemplateDialog({
  programId,
  defaultName,
  open,
  onClose,
}: SaveAsTemplateDialogProps) {
  const pushToast = useToastStore((s) => s.push);
  const save = useSaveAsTemplate(programId);
  const nameId = useId();
  const titleId = useId();

  const [name, setName] = useState(defaultName);
  const [visibility, setVisibility] = useState<TemplateVisibility>("private");

  // Re-seed the fields each time the dialog opens (a different row / fresh edit).
  useEffect(() => {
    if (open) {
      setName(defaultName);
      setVisibility("private");
    }
  }, [open, defaultName]);

  const trimmed = name.trim();
  const canSave = trimmed.length > 0 && !save.isPending;

  const onSubmit = () => {
    if (!canSave) return;
    save.mutate(
      { name: trimmed, visibility },
      {
        onSuccess: () => {
          pushToast({ kind: "success", message: "Saved as a template." });
          onClose();
        },
        onError: (e) =>
          pushToast({
            kind: "error",
            message: (e as unknown as ApiError)?.message ?? "Could not save template.",
          }),
      },
    );
  };

  return (
    <Sheet open={open} onClose={onClose} aria-labelledby={titleId}>
      <form
        className="sat"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        <div className="pw-kicker" id={titleId}>
          Save as template
        </div>
        <p className="sat-sub">
          A reusable copy appears in Browse templates. This program is left unchanged.
        </p>

        <label className="sat-label" htmlFor={nameId}>
          Template name
        </label>
        <input
          id={nameId}
          className="sat-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Template name"
          autoFocus
          maxLength={120}
        />

        <div className="sat-label" style={{ marginTop: 14 }}>
          Visibility
        </div>
        <div className="mini-seg" role="group" aria-label="Template visibility">
          <button
            type="button"
            className={`ms ${visibility === "private" ? "on" : ""}`}
            aria-pressed={visibility === "private"}
            onClick={() => setVisibility("private")}
          >
            Private to me
          </button>
          <button
            type="button"
            className={`ms ${visibility === "shared" ? "on" : ""}`}
            aria-pressed={visibility === "shared"}
            onClick={() => setVisibility("shared")}
          >
            Shared with partners
          </button>
        </div>

        <div className="sat-actions">
          <button type="button" className="sat-btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="sat-btn primary" disabled={!canSave}>
            {save.isPending ? "Saving…" : "Save template"}
          </button>
        </div>
      </form>
    </Sheet>
  );
}
