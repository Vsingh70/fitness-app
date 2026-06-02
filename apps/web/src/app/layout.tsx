import "./globals.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Gym",
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
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
