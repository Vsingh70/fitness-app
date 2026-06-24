"use client";

import { Lock, MoreHorizontal, Trash2, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useMe } from "@/lib/hooks/me";
import { useCopyTemplate, useDeleteTemplate, useTemplates } from "@/lib/hooks/programs";
import type { ProgramTemplateSummary } from "@/lib/programs/types";

// Underline category filters. Values map to real ProgramGoal strings where they
// exist; "endurance" has no enum equivalent yet, so that chip shows an empty set.
const CATS = ["all", "hypertrophy", "strength", "endurance", "general"] as const;
const CAT_LABELS: Record<(typeof CATS)[number], string> = {
  all: "All",
  hypertrophy: "Hypertrophy",
  strength: "Strength",
  endurance: "Endurance",
  general: "General",
};

type Group = {
  key: "curated" | "mine" | "shared";
  label: string;
  blurb: string;
  items: ProgramTemplateSummary[];
};

/**
 * Browse templates (`.tw-*`): underline category filters over an editorial
 * gallery split into Curated / My templates / Shared by partners. Each row opens
 * the template detail; a per-row "Use this template" runs the same copy flow for
 * every group. User-saved rows carry an owner/visibility marker and a delete-own
 * affordance (the user's own templates only). The gallery reveals on load.
 */
export function BrowseTemplates() {
  const router = useRouter();
  const list = useTemplates();
  const me = useMe();
  const [cat, setCat] = useState<(typeof CATS)[number]>("all");

  const myId = me.data?.id ?? null;

  const groups = useMemo<Group[]>(() => {
    const items = (list.data?.items ?? []).filter((t) => cat === "all" || t.goal === cat);
    const mine: ProgramTemplateSummary[] = [];
    const curated: ProgramTemplateSummary[] = [];
    const shared: ProgramTemplateSummary[] = [];
    for (const t of items) {
      if (myId && t.owner_id === myId) mine.push(t);
      else if (t.owner_id == null) curated.push(t);
      else shared.push(t);
    }
    return [
      {
        key: "curated",
        label: "Curated",
        blurb: "Built-in starting points.",
        items: curated,
      },
      {
        key: "mine",
        label: "My templates",
        blurb: "Saved from your own programs.",
        items: mine,
      },
      {
        key: "shared",
        label: "Shared by partners",
        blurb: "Templates your partners shared.",
        items: shared,
      },
    ];
  }, [list.data, cat, myId]);

  const hasAny = groups.some((g) => g.items.length > 0);

  return (
    <div className="page-shell flex flex-col">
      <div className="tw-filters">
        {CATS.map((c) => (
          <button key={c} type="button" className={c === cat ? "on" : ""} onClick={() => setCat(c)}>
            {CAT_LABELS[c]}
          </button>
        ))}
      </div>

      {list.isLoading ? (
        <p className="text-text-secondary">Loading…</p>
      ) : list.isError ? (
        <p className="text-destructive">Could not load templates.</p>
      ) : !hasAny ? (
        <p className="text-text-tertiary py-4 text-sm">No templates for this goal.</p>
      ) : (
        groups
          .filter((g) => g.items.length > 0)
          .map((g) => (
            <section className="tw-group" key={g.key}>
              <div className="tw-group-h">
                <span className="t">{g.label}</span>
                <span className="b">{g.blurb}</span>
              </div>
              <RevealGroup className="tw-gallery">
                {g.items.map((t) => (
                  <RevealItem key={t.id}>
                    <TemplateCard
                      template={t}
                      mine={Boolean(myId && t.owner_id === myId)}
                      onOpen={() => router.push(`/programs/templates/${t.slug}`)}
                    />
                  </RevealItem>
                ))}
              </RevealGroup>
            </section>
          ))
      )}
    </div>
  );
}

function TemplateCard({
  template: t,
  mine,
  onOpen,
}: {
  template: ProgramTemplateSummary;
  mine: boolean;
  onOpen: () => void;
}) {
  const router = useRouter();
  const pushToast = useToastStore((s) => s.push);
  const copy = useCopyTemplate();
  const del = useDeleteTemplate();

  const [menuOpen, setMenuOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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

  const onUse = () =>
    copy.mutate(t.slug, {
      onSuccess: (program) => router.push(`/programs/${program.id}`),
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not use this template.",
        }),
    });

  const onDelete = () => {
    setConfirming(false);
    del.mutate(t.slug, {
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not delete this template.",
        }),
    });
  };

  return (
    <div className="tw-tpl">
      <button type="button" className="tw-tpl-body" onClick={onOpen}>
        <div className="dl">{t.goal.replace(/_/g, " ")}</div>
        <div className="nm">{t.name}</div>
        {t.description ? <div className="de">{t.description}</div> : <div className="de" />}
        <div className="meta">
          <span>
            <b>{t.microcycle_length}</b>-slot
          </span>
          <span>
            <b>{t.mesocycle_length_microcycles}</b> micro
          </span>
          {mine ? (
            <span className="own">
              {t.visibility === "shared" ? <Users size={11} /> : <Lock size={11} />}
              {t.visibility === "shared" ? "Shared" : "Private"}
            </span>
          ) : t.author ? (
            <span>{t.author}</span>
          ) : null}
        </div>
      </button>

      <div className="tw-tpl-foot">
        {confirming ? (
          <span className="tw-confirm">
            <button type="button" className="del-yes" onClick={onDelete} disabled={del.isPending}>
              {del.isPending ? "Deleting…" : "Delete"}
            </button>
            <button type="button" className="del-no" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </span>
        ) : (
          <button type="button" className="tw-use" onClick={onUse} disabled={copy.isPending}>
            {copy.isPending ? "Copying…" : "Use this template"}
          </button>
        )}

        {mine && !confirming ? (
          <div className="aw-overflow" ref={menuRef}>
            <button
              type="button"
              className="ovf-btn"
              aria-label={`More actions for ${t.name}`}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <MoreHorizontal size={15} />
            </button>
            {menuOpen ? (
              <div className="ovf-menu" role="menu">
                <button
                  type="button"
                  role="menuitem"
                  className="ovf-item danger"
                  onClick={() => {
                    setMenuOpen(false);
                    setConfirming(true);
                  }}
                >
                  <Trash2 size={14} />
                  Delete template
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
