"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, PlayCircle } from "lucide-react";

import { HELP_SECTIONS } from "./help-content";
import { useToastStore } from "@/components/ui/toast";
import { useTutorialStore } from "@/lib/hooks/use-tutorial";

export default function HelpPage() {
  const router = useRouter();
  const reset = useTutorialStore((s) => s.reset);
  const start = useTutorialStore((s) => s.start);
  const pushToast = useToastStore((s) => s.push);

  const replayTutorial = () => {
    reset();
    pushToast({ kind: "info", message: "Starting the tour…" });
    // Go to Today, where every tour target is on screen, then start it.
    router.push("/");
    window.setTimeout(start, 450);
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <header className="mb-8">
        <p className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.12em]">
          Guide
        </p>
        <h1 className="font-serif text-[28px] font-medium tracking-tight">Help &amp; how-to</h1>
        <p className="text-text-secondary mt-1.5 text-sm leading-snug">
          What each screen is for, the key things you can do, and a quick example to get you
          going.
        </p>
      </header>

      {/* Replay tutorial */}
      <div className="border-border bg-surface-elevated mb-9 flex flex-col gap-3 rounded-[var(--radius-sheet)] border p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-text text-[15px] font-semibold">Replay the welcome tour</h2>
          <p className="text-text-secondary mt-0.5 text-sm leading-snug">
            Run the interactive spotlight tour of the main navigation again.
          </p>
        </div>
        <button
          type="button"
          onClick={replayTutorial}
          className="bg-accent text-accent-foreground inline-flex shrink-0 items-center justify-center gap-2 rounded-[var(--radius-button)] px-4 py-2 text-sm font-semibold"
        >
          <PlayCircle className="h-4 w-4" aria-hidden />
          Start tour
        </button>
      </div>

      {/* Per-page guides */}
      <div className="flex flex-col gap-7">
        {HELP_SECTIONS.map((s) => (
          <section
            key={s.id}
            id={s.id}
            className="border-border border-t pt-6 first:border-t-0 first:pt-0"
          >
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-serif text-[21px] font-medium tracking-tight">{s.page}</h2>
              <Link
                href={s.href}
                className="text-accent inline-flex items-center gap-1 text-xs font-semibold"
              >
                Open <ArrowRight className="h-3 w-3" aria-hidden />
              </Link>
            </div>

            <p className="text-text-secondary mt-2 text-sm leading-relaxed">{s.whatItsFor}</p>

            <h3 className="text-text-tertiary mt-4 text-[11px] font-semibold uppercase tracking-[0.1em]">
              What you can do
            </h3>
            <ul className="mt-1.5 flex flex-col gap-1.5">
              {s.keyActions.map((a, i) => (
                <li key={i} className="text-text flex gap-2 text-sm leading-snug">
                  <span className="bg-accent mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full" aria-hidden />
                  <span>{a}</span>
                </li>
              ))}
            </ul>

            {/* Example */}
            <div className="bg-accent-soft mt-4 rounded-[var(--radius-card)] p-3.5">
              <h3 className="text-text text-[13px] font-semibold">
                Example · {s.example.title}
              </h3>
              <ol className="mt-2 flex flex-col gap-1.5">
                {s.example.steps.map((step, i) => (
                  <li key={i} className="text-text-secondary flex gap-2.5 text-sm leading-snug">
                    <span className="text-accent font-serif text-[13px] font-semibold tabular-nums">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
