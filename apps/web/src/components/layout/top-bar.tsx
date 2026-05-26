import type { ReactNode } from "react";

interface TopBarProps {
  /** Reserved for a 'workout in progress' chip filled by later tasks. */
  workoutInProgressSlot?: ReactNode;
  title?: string;
}

export function TopBar({ workoutInProgressSlot, title }: TopBarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-bg/90 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-3">
        <span className="text-base font-semibold tracking-tight md:hidden">Gym</span>
        {title ? <h1 className="text-sm font-medium text-text-secondary">{title}</h1> : null}
      </div>
      <div className="flex items-center gap-3">{workoutInProgressSlot}</div>
    </header>
  );
}
