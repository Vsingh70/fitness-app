"use client";

import { cn } from "@/lib/cn";

interface Tab<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  tabs: readonly Tab<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
  ariaLabel?: string;
}

export function UnderlineTabs<T extends string>({
  tabs,
  value,
  onChange,
  className,
  ariaLabel,
}: Props<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn("border-border flex gap-[18px] border-b", className)}
    >
      {tabs.map((tab) => (
        <button
          key={tab.value}
          role="tab"
          type="button"
          aria-selected={value === tab.value}
          onClick={() => onChange(tab.value)}
          className={cn(
            "-mb-px border-b-[1.5px] border-transparent pb-[7px] text-xs font-semibold tracking-[0.08em] uppercase",
            "transition-colors duration-150 ease-out",
            value === tab.value ? "text-text border-text" : "text-text-secondary hover:text-text",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
