"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Reveal } from "@/components/motion/Reveal";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useCopyTemplate, useTemplate } from "@/lib/hooks/programs";

type TemplateSlotExercise = {
  slug_key: string;
  sets: number;
  reps_low?: number;
  reps_high?: number;
};

type TemplateSlot = {
  name: string;
  is_rest_day?: boolean;
  exercises: TemplateSlotExercise[];
};

/**
 * Template preview (`.dw-*`): serif hero + spec strip + the slot-by-slot
 * breakdown (rest slots rendered as a quiet rest state), and a "Use this
 * template" action that copies it into a new editable program and drops the user
 * onto that program. The hero reveals; the slot grid staggers in on load.
 */
export function TemplateDetail({ slug }: { slug: string }) {
  const router = useRouter();
  const pushToast = useToastStore((s) => s.push);
  const template = useTemplate(slug);
  const copy = useCopyTemplate();

  const onUse = () =>
    copy.mutate(slug, {
      onSuccess: (program) => router.push(`/programs/${program.id}`),
      onError: (e) =>
        pushToast({
          kind: "error",
          message: (e as unknown as ApiError)?.message ?? "Could not use this template.",
        }),
    });

  if (template.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (template.isError || !template.data)
    return <p className="text-destructive">Could not load template.</p>;

  const t = template.data;
  const slots = (t.data as { slots?: TemplateSlot[] }).slots ?? [];
  const slugMap = (t.data as { slug_map?: Record<string, string> }).slug_map ?? {};
  const goal = t.goal.replace(/_/g, " ");
  const trainingCount = slots.filter((s) => !s.is_rest_day).length;

  return (
    <div className="page-shell flex flex-col">
      <div className="mb-5 flex items-center justify-between gap-4">
        <p className="text-text-tertiary text-xs">
          <Link href="/programs" className="hover:text-text">
            Programs
          </Link>{" "}
          ›{" "}
          <Link href="/programs/templates" className="hover:text-text">
            Templates
          </Link>{" "}
          ›
        </p>
        <Button type="button" size="sm" onClick={onUse} disabled={copy.isPending}>
          {copy.isPending ? "Copying…" : "Use this template"}
        </Button>
      </div>

      <Reveal>
        <div className="dw-hero">
          <div className="dl">
            Template · <span className="capitalize">{goal}</span>
          </div>
          <h2>{t.name}</h2>
          {t.description ? <p>{t.description}</p> : null}
          <div className="dw-specs">
            <Spec value={`${t.microcycle_length}-slot`} label="Microcycle" />
            <Spec value={`${trainingCount} training`} label="In rotation" />
            <Spec value={`${t.mesocycle_length_microcycles} micro`} label="Mesocycle" />
            <Spec value={goal} label="Goal" capitalize />
          </div>
        </div>
      </Reveal>

      <RevealGroup className="dw-days">
        {slots.map((slot, idx) => (
          <RevealItem key={`${slot.name}-${idx}`}>
            <div className={`dw-day ${slot.is_rest_day ? "rest" : ""}`}>
              <div className="dl">Slot {idx + 1}</div>
              <div className="nm">{slot.name}</div>
              {slot.is_rest_day ? (
                <div className="rest-note">Rest day, no exercises</div>
              ) : (
                slot.exercises.map((ex, j) => {
                  const realSlug = slugMap[ex.slug_key] ?? ex.slug_key;
                  return (
                    <div className="ex" key={j}>
                      <span className="nm-ex">{realSlug.replace(/-/g, " ")}</span>
                      <span className="sr">{schemeString(ex)}</span>
                    </div>
                  );
                })
              )}
            </div>
          </RevealItem>
        ))}
      </RevealGroup>
    </div>
  );
}

function schemeString(ex: { sets: number; reps_low?: number; reps_high?: number }): string {
  if (ex.reps_low == null) return `${ex.sets}×`;
  const reps =
    ex.reps_high && ex.reps_high !== ex.reps_low
      ? `${ex.reps_low}–${ex.reps_high}`
      : String(ex.reps_low);
  return `${ex.sets}×${reps}`;
}

function Spec({
  value,
  label,
  capitalize,
}: {
  value: string;
  label: string;
  capitalize?: boolean;
}) {
  return (
    <div className="s">
      <div className={`v ${capitalize ? "capitalize" : ""}`}>{value}</div>
      <div className="l">{label}</div>
    </div>
  );
}
