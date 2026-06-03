"use client";

import { useEffect } from "react";
import { create } from "zustand";

export type Theme = "system" | "light" | "dark";
export type Accent = "blue" | "indigo" | "mint" | "orange" | "pink";

export const ACCENTS: Accent[] = ["blue", "indigo", "mint", "orange", "pink"];

const THEME_KEY = "om.theme";
const ACCENT_KEY = "om.accent";

function isTheme(v: string | null): v is Theme {
  return v === "system" || v === "light" || v === "dark";
}

function isAccent(v: string | null): v is Accent {
  return v != null && (ACCENTS as string[]).includes(v);
}

function readTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const v = window.localStorage.getItem(THEME_KEY);
  return isTheme(v) ? v : "system";
}

function readAccent(): Accent {
  if (typeof window === "undefined") return "blue";
  const v = window.localStorage.getItem(ACCENT_KEY);
  return isAccent(v) ? v : "blue";
}

interface ThemeStore {
  theme: Theme;
  accent: Accent;
  setTheme: (t: Theme) => void;
  setAccent: (a: Accent) => void;
}

export const useThemeStore = create<ThemeStore>((set) => ({
  theme: readTheme(),
  accent: readAccent(),
  setTheme: (theme) => {
    if (typeof window !== "undefined") window.localStorage.setItem(THEME_KEY, theme);
    set({ theme });
  },
  setAccent: (accent) => {
    if (typeof window !== "undefined") window.localStorage.setItem(ACCENT_KEY, accent);
    set({ accent });
  },
}));

/**
 * Applies the current theme + accent to <html> as data-theme / data-accent.
 * Mount once near the app root. A matching inline script in the root layout
 * applies the same attributes before hydration to avoid a flash.
 */
export function useApplyTheme(): void {
  const theme = useThemeStore((s) => s.theme);
  const accent = useThemeStore((s) => s.accent);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute("data-accent", accent);
  }, [accent]);
}
