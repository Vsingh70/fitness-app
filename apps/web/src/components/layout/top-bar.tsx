import type { ReactNode } from "react";
import Link from "next/link";
import { HelpCircle, Settings } from "lucide-react";

interface TopBarProps {
  /** Reserved for a 'workout in progress' chip filled by later tasks. */
  workoutInProgressSlot?: ReactNode;
  title?: string;
  crumb?: string;
}

export function TopBar({ workoutInProgressSlot, title, crumb }: TopBarProps) {
  return (
    <header className="border-border bg-bg/[0.86] sticky top-0 z-20 border-b backdrop-blur-xl backdrop-saturate-150">
      <div className="page-shell flex min-h-[58px] items-center gap-4 py-[15px]">
        <div className="flex items-baseline gap-3">
          {crumb ? (
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
              {crumb}
            </span>
          ) : null}
          {title ? (
            <h1 className="font-serif text-xl font-medium tracking-tight">{title}</h1>
          ) : null}
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          {workoutInProgressSlot}
          <Link
            href="/help"
            aria-label="Help and how-to"
            data-tutorial="help"
            className="text-text-secondary hover:text-text hover:bg-surface-elevated border-border flex h-9 items-center gap-1.5 rounded-[var(--radius-button)] border px-2.5 transition-colors"
          >
            <HelpCircle className="h-[18px] w-[18px]" aria-hidden />
            <span className="hidden text-sm font-medium sm:inline">Help</span>
          </Link>
          <Link
            href="/settings"
            aria-label="Settings"
            data-tutorial="nav-settings"
            className="text-text-secondary hover:text-text hover:bg-surface-elevated border-border flex h-9 w-9 items-center justify-center rounded-[var(--radius-button)] border transition-colors"
          >
            <Settings className="h-[18px] w-[18px]" aria-hidden />
          </Link>
        </div>
      </div>
    </header>
  );
}
