"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function SettingRow({
  title,
  sub,
  children,
  destructive,
}: {
  title: string;
  sub?: string;
  children: ReactNode;
  destructive?: boolean;
}) {
  return (
    <div className="border-border grid grid-cols-[1fr_auto] items-center gap-4 border-b px-4 py-[14px] last:border-b-0">
      <div className="min-w-0">
        <div className={cn("text-sm font-medium", destructive ? "text-destructive" : "text-text")}>
          {title}
        </div>
        {sub ? <div className="text-text-tertiary mt-0.5 text-xs">{sub}</div> : null}
      </div>
      <div className="flex items-center justify-end">{children}</div>
    </div>
  );
}

export interface SegOption<T extends string> {
  value: T;
  label: string;
}

export function SegControl<T extends string>({
  value,
  options,
  onChange,
  disabled,
  "aria-label": ariaLabel,
}: {
  value: T;
  options: SegOption<T>[];
  onChange: (v: T) => void;
  disabled?: boolean;
  "aria-label"?: string;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="border-border bg-surface inline-flex rounded-[9px] border p-[3px]"
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
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              active
                ? "bg-surface-elevated text-text font-semibold shadow-[var(--shadow-1)]"
                : "text-text-secondary hover:text-text",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function Toggle({
  checked,
  onChange,
  disabled,
  "aria-label": ariaLabel,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  "aria-label"?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative h-[26px] w-11 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-success" : "bg-border-strong",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-[22px] w-[22px] rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.2)] transition-[left]",
          checked ? "left-5" : "left-0.5",
        )}
      />
    </button>
  );
}
