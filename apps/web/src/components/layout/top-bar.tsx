import type { ReactNode } from "react";

interface TopBarProps {
  /** Reserved for a 'workout in progress' chip filled by later tasks. */
  workoutInProgressSlot?: ReactNode;
  title?: string;
  crumb?: string;
}

export function TopBar({ workoutInProgressSlot, title, crumb }: TopBarProps) {
  return (
    <header className="border-border bg-bg/[0.86] sticky top-0 z-20 flex min-h-[58px] items-center gap-4 border-b px-4 py-[15px] backdrop-blur-xl backdrop-saturate-150 md:px-8">
      <div className="flex items-baseline gap-3">
        {crumb ? (
          <span className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.14em]">
            {crumb}
          </span>
        ) : null}
        {title ? (
          <h1 className="font-serif text-xl font-medium tracking-tight">{title}</h1>
        ) : null}
      </div>
      <div className="flex-1" />
      <div className="flex items-center gap-2">{workoutInProgressSlot}</div>
    </header>
  );
}
