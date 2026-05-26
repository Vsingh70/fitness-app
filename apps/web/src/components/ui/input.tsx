import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "border-border bg-surface h-10 w-full rounded-[var(--radius-button)] border px-3",
        "text-text placeholder:text-text-tertiary",
        "focus:border-accent focus:ring-accent/30 focus:ring-2 focus:outline-none",
        className,
      )}
      {...rest}
    />
  );
}
