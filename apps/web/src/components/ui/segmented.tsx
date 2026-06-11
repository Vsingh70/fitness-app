"use client";

import { cn } from "@/lib/cn";

interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  options: readonly Option<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
}

/**
 * Compact ink-filled segmented control (the spec's `.mini-seg`). The active
 * segment is filled with the text ink; inactive segments are quiet. Distinct
 * from `UnderlineTabs`, which is an underline-style page-level tab strip.
 */
export function MiniSegmented<T extends string>({
  options,
  value,
  onChange,
  disabled,
  className,
  ariaLabel,
}: Props<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        "border-border-strong inline-flex gap-0.5 rounded-[var(--radius-button)] border p-0.5",
        className,
      )}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={cn(
              "rounded-[5px] px-2.5 py-1 text-[11px] font-semibold tracking-[0.06em] uppercase",
              "transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-60",
              active ? "bg-text text-bg" : "text-text-secondary hover:text-text",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
