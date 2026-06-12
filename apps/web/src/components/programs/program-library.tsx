"use client";

import { Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useActivateProgram, useDeleteProgram } from "@/lib/hooks/programs";
import type { ProgramListItem } from "@/lib/programs/types";

/**
 * "My programs" library (`.aw-progs`): every program with an Active / Activate /
 * Restore label, a trash → confirm → delete affordance, and a dashed "+ Create a
 * new program". Used on the overview and as the lead block when nothing's active.
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
  const pushToast = useToastStore((s) => s.push);
  const activate = useActivateProgram(p.id);
  const del = useDeleteProgram();
  const [confirming, setConfirming] = useState(false);

  const onActivate = () =>
    activate.mutate(
      { start_date: new Date().toISOString().slice(0, 10), weekday_offset: 0, skip_existing: true },
      {
        onError: (e) =>
          pushToast({
            kind: "error",
            message: (e as unknown as ApiError)?.message ?? "Could not activate program.",
          }),
      },
    );

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
        <div className="meta capitalize">
          {p.weeks} wk · {p.goal} · {p.days_per_week}×/wk
        </div>
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
        <span className="act on">Active</span>
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
        <button
          type="button"
          className="del"
          aria-label={`Delete ${p.name}`}
          onClick={() => setConfirming(true)}
        >
          <Trash2 size={15} />
        </button>
      )}
    </div>
  );
}
