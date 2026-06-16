"use client";

import { useRouter } from "next/navigation";

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

/**
 * First-run programs onboarding (`.ow-*`). Shown when the user has zero programs:
 * two editorial choice cards — Follow a template (ink fill, recommended) → the
 * template gallery, or Build your own (outline) → the blank builder.
 */
export function ProgramsOnboarding() {
  const router = useRouter();

  return (
    <div className="ow-wrap">
      <div className="pw-kicker" style={{ textAlign: "center" }}>
        Welcome to Programs
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
        First time here — start from a proven template, or build your own from scratch. You can
        switch anytime.
      </p>

      <div className="ow-choice">
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

        <button type="button" className="ow-card" onClick={() => router.push("/programs/new")}>
          <div className="ek">Full control</div>
          <div className="eh">Build your own program</div>
          <div className="ed">
            Compose days, exercises, set/rep schemes and a progression strategy from a blank slate.
          </div>
          <div className="ar" style={{ color: "var(--color-accent)" }}>
            Start building <ArrowR />
          </div>
        </button>
      </div>
    </div>
  );
}
