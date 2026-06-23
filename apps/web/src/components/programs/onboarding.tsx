"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { Reveal } from "@/components/motion/Reveal";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useCreateProgram } from "@/lib/hooks/programs";

const ArrowR = ({ size = 14 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M5 12h14M13 5l7 7-7 7" />
  </svg>
);

interface ProgramsOnboardingProps {
  /**
   * `firstRun` is the zero-programs welcome (whole screen); otherwise this is the
   * `/programs/new` chooser reached from a library/spine "New program" action.
   */
  firstRun?: boolean;
}

/**
 * The new-program chooser (`.ow-*`): two editorial choice cards — Follow a
 * template (ink fill, recommended) → the template gallery, or Build your own
 * (outline) → a blank draft program that drops straight into the builder.
 *
 * This is the single entry point for creating *any* program, not first-run
 * only: it is the whole screen when the user has zero programs, and the
 * `/programs/new` route renders it for every later "New program" action.
 */
export function ProgramsOnboarding({ firstRun = false }: ProgramsOnboardingProps) {
  const router = useRouter();
  const pushToast = useToastStore((s) => s.push);
  const create = useCreateProgram();
  // Guard against a double tap spawning two draft programs while the create
  // mutation is in flight (and its own retry).
  const building = useRef(false);
  const [pending, setPending] = useState(false);

  const buildYourOwn = () => {
    if (building.current) return;
    building.current = true;
    setPending(true);
    create.mutate(
      {
        name: "New program",
        goal: "hypertrophy",
        periodization_mode: "block",
        auto_deload_on_stall: true,
        // Default scale; the builder's Intensity tracking control can switch it.
        intensity_mode: "rpe",
      },
      {
        onSuccess: (program) => router.replace(`/programs/${program.id}/edit`),
        onError: (e) => {
          building.current = false;
          setPending(false);
          pushToast({
            kind: "error",
            message: (e as unknown as ApiError)?.message ?? "Could not create program.",
          });
        },
      },
    );
  };

  return (
    <div className="ow-wrap">
      <Reveal>
        <div className="pw-kicker" style={{ textAlign: "center" }}>
          {firstRun ? "Welcome to Programs" : "New program"}
        </div>
        <h2 className="pw-serif" style={{ fontSize: 32, textAlign: "center", margin: "10px 0 6px" }}>
          How do you want to train?
        </h2>
        <p
          style={{
            textAlign: "center",
            color: "var(--color-text-secondary)",
            fontSize: 14,
            margin: "0 auto 28px",
            maxWidth: 430,
          }}
        >
          {firstRun
            ? "First time here — start from a proven template, or build your own from scratch. You can switch anytime."
            : "Start from a proven template, or build your own from a blank slate."}
        </p>
      </Reveal>

      <div className="ow-choice">
        <Reveal delay={0.06}>
          <button
            type="button"
            className="ow-card primary"
            onClick={() => router.push("/programs/templates")}
          >
            <div className="ek">Recommended</div>
            <div className="eh">Follow a template</div>
            <div className="ed">
              Pick a proven program — PPL, Upper/Lower, 5/3/1 and more. Copy it, tweak if you like,
              and start this week.
            </div>
            <div className="ar">
              Browse templates <ArrowR />
            </div>
          </button>
        </Reveal>

        <Reveal delay={0.12}>
          <button
            type="button"
            className="ow-card"
            onClick={buildYourOwn}
            disabled={pending}
            aria-busy={pending}
          >
            <div className="ek">Full control</div>
            <div className="eh">Build your own program</div>
            <div className="ed">
              Compose slots, exercises, set/rep schemes and a progression strategy from a blank
              slate.
            </div>
            <div className="ar" style={{ color: "var(--color-accent)" }}>
              {pending ? "Creating…" : "Start building"} <ArrowR />
            </div>
          </button>
        </Reveal>
      </div>
    </div>
  );
}
