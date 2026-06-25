#!/usr/bin/env node
/**
 * Bundle-size budget check (the static-weight layer of the perf suite).
 *
 * Reads the Next.js build output and compares each route's first-load client JS
 * (gzipped) against the budgets in perf/budgets.json. Run it after a build:
 *
 *   pnpm build && pnpm perf:bundle
 *
 * It is a ratchet: budgets are pinned near the current baseline so a regression
 * (for example pulling recharts into a route synchronously) fails CI, while a fix
 * lets the budget drop. If no build is present it prints a notice and exits 0 so
 * local runs are not blocked.
 */
import { gzipSync } from "node:zlib";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");
const NEXT_DIR = path.join(WEB_ROOT, ".next");
const MANIFEST = path.join(NEXT_DIR, "app-build-manifest.json");

const budgets = JSON.parse(
  readFileSync(path.join(WEB_ROOT, "perf", "budgets.json"), "utf8"),
).bundleKBGzip;

if (!existsSync(MANIFEST)) {
  console.log(
    "[perf:bundle] No build found (.next/app-build-manifest.json missing). " +
      "Run `pnpm build` first. Skipping.",
  );
  process.exit(0);
}

/** Normalize an app-router manifest key to a route path budgets can match. */
function normalize(key) {
  let r = key.replace(/\/page$/, "").replace(/\(.+?\)\//g, "");
  if (!r.startsWith("/")) r = "/" + r;
  return r === "" ? "/" : r;
}

function gzipKB(files) {
  let bytes = 0;
  for (const rel of files) {
    if (!rel.endsWith(".js")) continue;
    const full = path.join(NEXT_DIR, rel);
    if (existsSync(full)) bytes += gzipSync(readFileSync(full)).length;
  }
  return bytes / 1024;
}

const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
const pages = manifest.pages ?? {};

const rows = [];
let failed = false;

for (const [key, files] of Object.entries(pages)) {
  const route = normalize(key);
  const budget = budgets.routes[route] ?? budgets.global;
  const kb = gzipKB(files);
  const over = kb > budget;
  if (over) failed = true;
  rows.push({ route, kb: kb.toFixed(1), budget, status: over ? "OVER" : "ok" });
}

rows.sort((a, b) => Number(b.kb) - Number(a.kb));
console.log("\nRoute first-load JS (gzip KB) vs budget:\n");
for (const r of rows) {
  console.log(
    `  ${r.status === "OVER" ? "✗" : "✓"} ${r.route.padEnd(28)} ${String(r.kb).padStart(7)} KB  / ${r.budget} KB`,
  );
}
console.log("");

if (failed) {
  console.error("[perf:bundle] One or more routes exceed their budget. See perf/budgets.json.");
  process.exit(1);
}
console.log("[perf:bundle] All routes within budget.");
