"use client";

import { Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useActivateProgram, useDeleteProgram } from "@/lib/hooks/programs";
import type { ProgramListItem } from "@/lib/programs/types";

/**
 * The "My programs" library: every program with an activate / active label, an
 * inline-confirm trash delete, and a "create a new program" affordance. Used on
 * the active-program overview and as the lead block when nothing is active.
 */
export function ProgramLibrary({ items }: { items: ProgramListItem[] }) {
  return (
    <section>
      <div className="border-border mb-1 flex items-center justify-between border-b pb-2.5">
        <h2 className="text-text-secondary text-[11px] font-semibold tracking-[0.14em] uppercase">
          My programs
        </h2>
        <div className="flex items-center gap-4">
          <Link href="/programs/templates" className="text-text-tertiary hover:text-text text-xs">
            Browse templates
          </Link>
          <Link href="/programs/new" className="text-text-tertiary hover:text-text text-xs">
            + New program
          </Link>
        </div>
      </div>

      <div className="flex flex-col">
        {items.map((p) => (
          <ProgramRow key={p.id} program={p} />
        ))}
      </div>

      <Link
        href="/programs/new"
        className="border-border-strong text-text-secondary hover:border-text hover:text-text mt-4 flex items-center justify-center gap-2 rounded-[var(--radius-button)] border border-dashed px-4 py-3 text-[13px] font-semibold transition-colors"
      >
        <Plus className="h-4 w-4" aria-hidden /> Create a new program
      </Link>
    </section>
  );
}

function ProgramRow({ program: p }: { program: ProgramListItem }) {
  const pushToast = useToastStore((s) => s.push);
  const activate = useActivateProgram(p.id);
  const del = useDeleteProgram();
  const [confirming, setConfirming] = useState(false);

  const onActivate = () =>
    activate.mutate(
      {
        start_date: new Date().toISOString().slice(0, 10),
        weekday_offset: 0,
        skip_existing: true,
      },
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
    <div className="border-border grid grid-cols-[1fr_auto] items-center gap-4 border-b py-3.5">
      <Link href={`/programs/${p.id}`} className="min-w-0">
        <span
          className={`font-serif text-[16px] font-medium ${p.is_active ? "text-accent" : "text-text"}`}
        >
          {p.name}
        </span>
        <span className="text-text-tertiary ml-2 text-[12px] capitalize">
          {p.weeks}-week · {p.goal}
        </span>
      </Link>

      <div className="flex items-center gap-3">
        {p.is_active ? (
          <span className="text-accent text-[10px] font-semibold tracking-[0.1em] uppercase">
            Active
          </span>
        ) : (
          <button
            type="button"
            onClick={onActivate}
            disabled={activate.isPending}
            className="text-text-secondary hover:text-text text-[11px] font-semibold tracking-[0.06em] uppercase disabled:opacity-60"
          >
            {activate.isPending ? "Activating…" : "Activate"}
          </button>
        )}

        {confirming ? (
          <span className="flex items-center gap-2">
            <button
              type="button"
              onClick={onDelete}
              className="text-destructive text-[11px] font-semibold tracking-[0.06em] uppercase"
            >
              Delete
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="text-text-tertiary hover:text-text text-[11px]"
            >
              Cancel
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            aria-label="Delete program"
            className="text-text-tertiary hover:text-destructive flex h-7 w-7 items-center justify-center"
          >
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        )}
      </div>
    </div>
  );
}
