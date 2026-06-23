"use client";

import { Bookmark, Copy, MoreHorizontal, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import {
  useActivateProgram,
  useDeactivateAnyProgram,
  useDeleteProgram,
  useDuplicateProgram,
} from "@/lib/hooks/programs";
import type { ProgramGoal, ProgramListItem } from "@/lib/programs/types";

import { SaveAsTemplateDialog } from "./save-as-template-dialog";

const GOAL_LABEL: Record<ProgramGoal, string> = {
  hypertrophy: "hypertrophy",
  strength: "strength",
  powerbuilding: "powerbuilding",
  fat_loss: "fat loss",
  general: "general",
  custom: "custom",
};

/**
 * "My programs" library (`.aw-progs`): every program with an Activate / Active
 * (hover-to-deactivate) affordance, a per-row overflow (Duplicate / Save as
 * template), a separate trash → confirm → delete, and a dashed "+ Create a new
 * program" that routes to the new-program chooser.
 */
export function ProgramLibrary({ items }: { items: ProgramListItem[] }) {
  return (
    <div className="aw-progs">
      <div className="aw-week-h">
        <span className="t">My programs</span>
        <Link href="/programs/new" className="pw-link">
          + New program
        </Link>
      </div>

      {items.map((p) => (
        <ProgramRow key={p.id} program={p} />
      ))}

      <Link href="/programs/new" className="aw-newprog">
        + Create a new program
      </Link>
    </div>
  );
}

function ProgramRow({ program: p }: { program: ProgramListItem }) {
  const router = useRouter();
  const pushToast = useToastStore((s) => s.push);
  const activate = useActivateProgram(p.id);
  const deactivate = useDeactivateAnyProgram();
  const duplicate = useDuplicateProgram();
  const del = useDeleteProgram();

  const [confirming, setConfirming] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Dismiss the overflow menu on an outside click or Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  const meta = `${p.microcycle_length}-slot cycle · ${p.mesocycle_length_microcycles} micro · ${
    GOAL_LABEL[p.goal] ?? p.goal
  }`;

  const onActivate = () =>
    activate.mutate(undefined, {
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not activate program.",
        }),
    });

  const onDeactivate = () => {
    setMenuOpen(false);
    deactivate.mutate(p.id, {
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not deactivate program.",
        }),
    });
  };

  const onDuplicate = () => {
    setMenuOpen(false);
    duplicate.mutate(p.id, {
      onSuccess: ({ program }) => router.push(`/programs/${program.id}/edit`),
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not duplicate program.",
        }),
    });
  };

  const onDelete = () => {
    setConfirming(false);
    del.mutate(p.id, {
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not delete program.",
        }),
    });
  };

  return (
    <div className={`aw-prog-row ${p.is_active ? "active" : ""}`}>
      <Link href={`/programs/${p.id}`} className="min-w-0">
        <div className="nm">{p.name}</div>
        <div className="meta">{meta}</div>
      </Link>

      {confirming ? (
        <span className="act" style={{ whiteSpace: "nowrap" }}>
          <button type="button" className="act danger" onClick={onDelete}>
            Delete
          </button>
          <span style={{ color: "var(--color-text-tertiary)", margin: "0 6px" }}>·</span>
          <button type="button" className="act link" onClick={() => setConfirming(false)}>
            Cancel
          </button>
        </span>
      ) : p.is_active ? (
        // Active: the "Active" label swaps to a destructive Deactivate on hover or
        // keyboard focus (pointer); touch users reach Deactivate via the overflow.
        <span className="act-swap" data-pending={deactivate.isPending || undefined}>
          <span className="act on rest">{deactivate.isPending ? "…" : "Active"}</span>
          <button
            type="button"
            className="act danger hover"
            onClick={onDeactivate}
            disabled={deactivate.isPending}
          >
            Deactivate
          </button>
        </span>
      ) : (
        <button
          type="button"
          className="act link"
          onClick={onActivate}
          disabled={activate.isPending}
        >
          {activate.isPending ? "Activating…" : "Activate"}
        </button>
      )}

      {confirming ? (
        <span />
      ) : (
        <div className="aw-prog-tools">
          <div className="aw-overflow" ref={menuRef}>
            <button
              type="button"
              className="ovf-btn"
              aria-label={`More actions for ${p.name}`}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <MoreHorizontal size={15} />
            </button>

            {menuOpen ? (
              <div className="ovf-menu" role="menu">
                {p.is_active ? (
                  <button type="button" role="menuitem" className="ovf-item danger" onClick={onDeactivate}>
                    Deactivate
                  </button>
                ) : null}
                <button
                  type="button"
                  role="menuitem"
                  className="ovf-item"
                  onClick={onDuplicate}
                  disabled={duplicate.isPending}
                >
                  <Copy size={14} />
                  {duplicate.isPending ? "Duplicating…" : "Duplicate"}
                </button>
                <button
                  type="button"
                  role="menuitem"
                  className="ovf-item"
                  onClick={() => {
                    setMenuOpen(false);
                    setSavingTemplate(true);
                  }}
                >
                  <Bookmark size={14} />
                  Save as template
                </button>
              </div>
            ) : null}
          </div>

          <button
            type="button"
            className="del"
            aria-label={`Delete ${p.name}`}
            onClick={() => setConfirming(true)}
          >
            <Trash2 size={15} />
          </button>
        </div>
      )}

      <SaveAsTemplateDialog
        programId={p.id}
        defaultName={`${p.name} template`}
        open={savingTemplate}
        onClose={() => setSavingTemplate(false)}
      />
    </div>
  );
}
