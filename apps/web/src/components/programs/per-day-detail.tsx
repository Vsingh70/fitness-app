"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { Reveal } from "@/components/motion/Reveal";
import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useProgram } from "@/lib/hooks/programs";
import { useCreateEmptySession } from "@/lib/hooks/workouts";
import { snappy } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import { useActiveSession } from "@/lib/state/active-session";
import type { IntensityMode, ProgramDayExercise } from "@/lib/programs/types";

const STRATEGY_LABELS: Record<string, string> = {
  linear: "Linear",
  double_progression: "Double progression",
  rpe_based: "RPE-based",
  none: "No auto-progression",
};

/**
 * Per-slot prescription (`.xw-*`): slot hero + one scheme row per exercise
 * (Sets / Reps / {RPE|RIR} / Rest) and a progression line, plus a Start action
 * that opens a fresh session named after the slot. A rest slot shows the quiet
 * rest state with no exercise rows. The intensity column follows the program's
 * global mode and is hidden when it is "off"; the reps value reflects each
 * exercise's own rep_mode (a range or a single target). The hero reveals; the
 * exercise list staggers in on load.
 */
export function PerDayDetail({ programId, dayId }: { programId: string; dayId: string }) {
  const router = useRouter();
  const pushToast = useToastStore((s) => s.push);
  const program = useProgram(programId);
  const createEmpty = useCreateEmptySession();
  const setActive = useActiveSession((s) => s.setActive);
  const { reduced } = useReducedMotionSafe();

  const p = program.data;
  const day = p?.days.find((d) => d.id === dayId) ?? null;
  const slotNumber = p ? p.days.findIndex((d) => d.id === dayId) + 1 : 0;

  const exerciseIds = useMemo(() => (day ? day.exercises.map((e) => e.exercise_id) : []), [day]);
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  if (program.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (program.isError || !p) return <p className="text-destructive">Could not load program.</p>;
  if (!day) return <p className="text-text-secondary">Slot not found.</p>;

  const onStart = () =>
    createEmpty.mutate(
      { name: day.name },
      {
        onSuccess: (session) => {
          setActive(session.id, session.started_at);
          router.push(`/workouts/${session.id}`);
        },
        onError: (e) =>
          pushToast({
            kind: "error",
            message: (e as unknown as ApiError)?.message ?? "Could not start the session.",
          }),
      },
    );

  const goal = p.goal.replace(/_/g, " ");
  const crumb = (
    <p className="text-text-tertiary text-xs">
      <Link href={`/programs/${p.id}`} className="hover:text-text">
        {p.name}
      </Link>{" "}
      ›
    </p>
  );

  if (day.is_rest_day) {
    return (
      <div className="page-shell flex flex-col">
        <div className="mb-5">{crumb}</div>
        <Reveal>
          <div className="xw-hero rest">
            <div className="dl">
              Slot {slotNumber} · <span className="capitalize">{goal}</span>
            </div>
            <h2>{day.name}</h2>
            <div className="meta" style={{ fontStyle: "italic" }}>
              Rest day, no exercises
            </div>
          </div>
        </Reveal>
        <p className="text-text-secondary mt-6 text-sm">
          Nothing scheduled for this slot — recover and come back for the next training slot.
        </p>
      </div>
    );
  }

  const intensityLabel = intensityHeader(p.intensity_mode);
  const workingSets = day.exercises.reduce((s, ex) => s + ex.target_sets, 0);
  const estMin = Math.round(workingSets * 2.5);
  const muscles = Array.from(
    new Set(
      day.exercises
        .map((ex) => metaMap.get(ex.exercise_id)?.primary_muscle as string | undefined)
        .filter((m): m is string => Boolean(m)),
    ),
  );
  const metaBits = [
    `${day.exercises.length} exercises`,
    `${workingSets} working sets`,
    `~${estMin} min`,
    ...(muscles.length ? [muscles.map(titleCase).join(" · ")] : []),
  ];

  return (
    <div className="page-shell flex flex-col">
      <div className="mb-5 flex items-center justify-between gap-4">
        {crumb}
        <motion.button
          type="button"
          onClick={onStart}
          disabled={createEmpty.isPending}
          transition={snappy}
          whileTap={reduced ? undefined : { scale: 0.985 }}
          className="bg-accent text-accent-foreground inline-flex h-[36px] items-center justify-center gap-2 rounded-[var(--radius-button)] px-[16px] text-[13px] font-semibold tracking-[0.01em] hover:brightness-105 disabled:opacity-60"
        >
          <svg width={14} height={14} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M6 4l14 8-14 8z" />
          </svg>
          {createEmpty.isPending ? "Starting…" : "Start workout"}
        </motion.button>
      </div>

      <Reveal>
        <div className="xw-hero">
          <div className="dl">
            Slot {slotNumber} · <span className="capitalize">{goal}</span>
          </div>
          <h2>{day.name}</h2>
          <div className="meta">{metaBits.join(" · ")}</div>
        </div>
      </Reveal>

      <RevealGroup>
        {day.exercises.map((ex, i) => {
          const muscle = metaMap.get(ex.exercise_id)?.primary_muscle as string | undefined;
          const cells: { label: string; value: string }[] = [
            { label: "Sets", value: String(ex.target_sets) },
            { label: "Reps", value: repsDisplay(ex) },
            ...(intensityLabel
              ? [{ label: intensityLabel, value: intensityDisplay(ex, p.intensity_mode) }]
              : []),
            { label: "Rest", value: ex.rest_seconds ? formatRest(ex.rest_seconds) : "—" },
          ];
          return (
            <RevealItem key={ex.id}>
              <div className="xw-ex">
                <div className="top">
                  <span className="idx">{String(i + 1).padStart(2, "0")}</span>
                  <span className="nm">{metaMap.get(ex.exercise_id)?.name ?? "Exercise"}</span>
                  {muscle ? <span className="tag">{titleCase(muscle)}</span> : null}
                </div>
                <div className="scheme">
                  {cells.map((c) => (
                    <div className="c" key={c.label}>
                      <div className="v">{c.value}</div>
                      <div className="l">{c.label}</div>
                    </div>
                  ))}
                </div>
                <div className="prog">
                  Progression —{" "}
                  <b>{STRATEGY_LABELS[ex.progression_strategy] ?? ex.progression_strategy}</b>
                </div>
              </div>
            </RevealItem>
          );
        })}
      </RevealGroup>
    </div>
  );
}

function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatRest(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, "0")}` : `${s}s`;
}

function intensityHeader(mode: IntensityMode): string | null {
  if (mode === "rpe") return "RPE";
  if (mode === "rir") return "RIR";
  return null;
}

function repsDisplay(ex: ProgramDayExercise): string {
  const low = ex.target_reps_low;
  const high = ex.target_reps_high;
  if (low == null) return "—";
  if (ex.rep_mode === "target" || high == null || high === low) return String(low);
  return `${low}–${high}`;
}

function intensityDisplay(ex: ProgramDayExercise, mode: IntensityMode): string {
  if (mode === "off") return "—";
  const low = mode === "rpe" ? ex.target_rpe_low : ex.target_rir_low;
  const high = mode === "rpe" ? ex.target_rpe_high : ex.target_rir_high;
  if (low == null) return "—";
  const lowStr = String(low);
  const highStr = high == null ? null : String(high);
  if (highStr == null || highStr === lowStr) return lowStr;
  return `${lowStr}–${highStr}`;
}
