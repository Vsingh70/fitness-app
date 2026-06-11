import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "border-border-strong bg-surface-elevated h-[42px] w-full rounded-[var(--radius-button)] border px-3 text-sm",
        "text-text placeholder:text-text-tertiary",
        "focus:border-accent focus:ring-accent-soft focus:ring-[3px] focus:outline-none",
        "transition-[border-color,box-shadow] duration-150 ease-out",
        className,
      )}
      {...rest}
    />
  );
}
