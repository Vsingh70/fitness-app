import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { STATIC } from "./budgets";

/**
 * Static performance guardrails. These read the source tree, never a browser, so
 * they run anywhere and are deterministic. They are ratchets: each assertion is a
 * ceiling pinned at the current baseline so any regression (more client
 * components, more always-on animation) fails, while performance fixes let the
 * ceilings drop.
 *
 * Why these matter:
 * - Every "use client" file forces hydration and blocks streaming. Fewer is faster.
 * - A client route page (page.tsx with "use client") opts the whole route out of
 *   server rendering. The audit flagged 22 of 28 route pages as client.
 * - A client root layout (layout.tsx) drags every nested route into client mode.
 * - Each file importing the motion library is a potential always-on animation; the
 *   route-transition Reveal in the app layout is the worst offender.
 */

const SRC = path.resolve(__dirname, "../../src");

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (entry === "node_modules" || entry === ".next") continue;
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(tsx?|jsx?)$/.test(entry)) out.push(full);
  }
  return out;
}

const allFiles = walk(SRC);
const isClient = (f: string) => /^\s*["']use client["']/m.test(readFileSync(f, "utf8"));
const importsMotion = (f: string) => /from\s+["']motion(\/|["'])/.test(readFileSync(f, "utf8"));

describe("client-component budget (static, ratchet)", () => {
  it(`keeps total "use client" files at or under ${STATIC.useClientFilesMax}`, () => {
    const count = allFiles.filter(isClient).length;
    expect(count, `"use client" files: ${count}`).toBeLessThanOrEqual(STATIC.useClientFilesMax);
  });

  it(`keeps client-rendered route pages at or under ${STATIC.clientRoutePagesMax}`, () => {
    const routePages = allFiles.filter((f) => f.endsWith(`${path.sep}page.tsx`));
    const clientRoutePages = routePages.filter(isClient);
    expect(
      clientRoutePages.length,
      `client route pages:\n${clientRoutePages.map((f) => "  " + path.relative(SRC, f)).join("\n")}`,
    ).toBeLessThanOrEqual(STATIC.clientRoutePagesMax);
  });

  it(`keeps client-rendered layouts at or under ${STATIC.clientLayoutsMax}`, () => {
    const layouts = allFiles.filter((f) => f.endsWith(`${path.sep}layout.tsx`));
    const clientLayouts = layouts.filter(isClient);
    expect(
      clientLayouts.length,
      `client layouts:\n${clientLayouts.map((f) => "  " + path.relative(SRC, f)).join("\n")}`,
    ).toBeLessThanOrEqual(STATIC.clientLayoutsMax);
  });

  it(`keeps files importing the motion library at or under ${STATIC.motionImportFilesMax}`, () => {
    const count = allFiles.filter(importsMotion).length;
    expect(count, `motion-importing files: ${count}`).toBeLessThanOrEqual(
      STATIC.motionImportFilesMax,
    );
  });
});
