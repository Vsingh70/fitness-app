"use client";

import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "destructive";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-foreground border border-transparent hover:brightness-105",
  secondary:
    "bg-transparent text-text border border-text hover:bg-text hover:text-bg",
  ghost:
    "bg-transparent text-text border border-transparent hover:bg-surface-elevated",
  destructive:
    "bg-destructive text-white border border-transparent hover:brightness-105",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "h-[34px] px-[14px] text-[13px] rounded-md",
  md: "h-10 px-4 text-sm",
  lg: "h-[42px] px-[18px] text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2",
        "rounded-[var(--radius-button)] font-semibold tracking-[0.01em]",
        "transition-[background-color,color,filter,transform] duration-150 ease-out",
        "active:scale-[0.985] disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      {...rest}
    />
  );
}
