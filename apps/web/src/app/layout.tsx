import "./globals.css";

import type { Metadata, Viewport } from "next";
import { Source_Serif_4 } from "next/font/google";
import type { ReactNode } from "react";

import { Providers } from "./providers";

/* Branded editorial serif for titles & figures. Routed into --font-serif
 * (see tokens.css / globals.css) ahead of the system serif fallback stack.
 * `display: "swap"` + a matching fallback keep CLS near zero. */
const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-serif-display",
  fallback: [
    "Iowan Old Style",
    "Palatino Linotype",
    "Palatino",
    "Georgia",
    "Times New Roman",
    "serif",
  ],
});

export const metadata: Metadata = {
  title: "VGains",
  description: "Training operating system.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "white" },
    { media: "(prefers-color-scheme: dark)", color: "black" },
  ],
};

// Applies persisted theme + accent before hydration to avoid a flash.
const THEME_INIT = `(function(){try{var t=localStorage.getItem("om.theme");var a=localStorage.getItem("om.accent");var r=document.documentElement;if(t==="light"||t==="dark")r.setAttribute("data-theme",t);if(["blue","indigo","mint","orange","pink"].indexOf(a)>=0)r.setAttribute("data-accent",a);}catch(e){}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={sourceSerif.variable}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
