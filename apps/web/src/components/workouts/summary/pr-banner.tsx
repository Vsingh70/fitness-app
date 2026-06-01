"use client";

import Link from "next/link";

interface PrItem {
  exerciseId: string;
  exerciseName: string;
  weightKg: number | null;
  reps: number | null;
  estimated1Rm: number | null;
}

interface Props {
  prs: PrItem[];
}

export function PrBanner({ prs }: Props) {
  if (prs.length === 0) return null;

  const headline =
    prs.length === 1
      ? `Personal record on ${prs[0]!.exerciseName}`
      : `${prs.length} personal records this session`;

  return (
    <div
      className="border-border bg-surface-elevated relative grid items-center gap-5 overflow-hidden rounded-[var(--radius-card)] border px-7 py-6 md:grid-cols-[auto_1fr_auto]"
      style={{
        backgroundImage:
          "radial-gradient(600px 240px at 0% 0%, var(--color-pr-soft), transparent 65%)",
      }}
    >
      <div
        className="font-serif bg-pr grid h-14 w-14 place-items-center rounded-[10px] text-[20px] font-semibold"
        style={{ color: "oklch(0.30 0.10 80)" }}
      >
        PR
      </div>
      <div className="min-w-0">
        <h2 className="font-serif text-text text-[22px] font-medium leading-tight tracking-tight">
          {headline}
        </h2>
        <ul className="text-text-secondary mt-1 flex flex-col gap-0.5 text-[13px]">
          {prs.slice(0, 3).map((pr) => (
            <li key={pr.exerciseId}>
              <span className="text-text font-medium">{pr.exerciseName}</span>
              {pr.weightKg !== null && pr.reps !== null ? (
                <>
                  {" · "}
                  <b className="text-text font-serif font-medium tabular-nums">
                    {pr.weightKg} kg × {pr.reps}
                  </b>
                </>
              ) : null}
              {pr.estimated1Rm !== null ? (
                <>
                  {" · est. 1RM "}
                  <b className="text-text font-serif font-medium tabular-nums">
                    {pr.estimated1Rm.toFixed(1)} kg
                  </b>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      {prs.length === 1 ? (
        <Link
          href={`/exercises/${prs[0]!.exerciseId}`}
          className="border-text text-text hover:bg-text hover:text-bg inline-flex h-[42px] items-center justify-center rounded-[var(--radius-button)] border px-[18px] text-sm font-semibold tracking-[0.01em]"
        >
          Open exercise
        </Link>
      ) : null}
    </div>
  );
}
