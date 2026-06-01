import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "border-border bg-surface-elevated rounded-[var(--radius-card)] border",
        className,
      )}
      {...rest}
    />
  );
}

export function CardHeader({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-2 px-[18px] pt-4 pb-[10px]",
        "text-text-secondary text-xs font-semibold uppercase tracking-[0.12em]",
        className,
      )}
      {...rest}
    />
  );
}

export function CardContent({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-[18px] pb-[18px] pt-[10px]", className)} {...rest} />;
}
