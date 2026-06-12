"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { useCreateProgram } from "@/lib/hooks/programs";

/**
 * "Build your own" entry. The editorial builder works on a real program, so we
 * create a blank draft up front and drop straight into it. A ref guards against
 * React's double-invoke (and the create mutation's own retry) so we never spawn
 * two programs.
 */
export default function NewProgramPage() {
  const router = useRouter();
  const create = useCreateProgram();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    create.mutate(
      {
        name: "New program",
        goal: "hypertrophy",
        weeks: 6,
        days_per_week: 4,
        periodization_mode: "block",
        auto_deload_on_stall: true,
        // Default scale; the builder's Intensity tracking control can switch it.
        intensity_mode: "rpe",
      },
      {
        onSuccess: (program) => router.replace(`/programs/${program.id}/edit`),
        onError: () => {
          started.current = false;
        },
      },
    );
    // create.mutate and router are stable; intentionally run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <p className="text-text-secondary py-10 text-center text-sm">
      {create.isError ? "Could not create program. Please try again." : "Creating your program…"}
    </p>
  );
}
