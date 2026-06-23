"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useTemplates } from "@/lib/hooks/programs";
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

/**
 * Browse templates (`.tw-*`): underline category filters over a two-column
 * editorial gallery, each row a hairline-separated template. Tapping a row opens
 * the template detail.
 */
export function BrowseTemplates() {
  const router = useRouter();
  const list = useTemplates();
  const [cat, setCat] = useState<(typeof CATS)[number]>("all");

  return (
    <div className="mx-auto flex max-w-5xl flex-col">
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
      ) : (
        <Gallery
          items={list.data?.items ?? []}
          cat={cat}
          onOpen={(slug) => router.push(`/programs/templates/${slug}`)}
        />
      )}
    </div>
  );
}

function Gallery({
  items,
  cat,
  onOpen,
}: {
  items: ProgramTemplateSummary[];
  cat: (typeof CATS)[number];
  onOpen: (slug: string) => void;
}) {
  const filtered = items.filter((t) => cat === "all" || t.goal === cat);
  if (filtered.length === 0) {
    return <p className="text-text-tertiary py-4 text-sm">No templates for this goal.</p>;
  }
  return (
    <div className="tw-gallery">
      {filtered.map((t) => (
        <button key={t.id} type="button" className="tw-tpl" onClick={() => onOpen(t.slug)}>
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
            {t.author ? <span>{t.author}</span> : null}
          </div>
        </button>
      ))}
    </div>
  );
}
