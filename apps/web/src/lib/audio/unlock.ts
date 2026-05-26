"use client";

/**
 * Browser audio requires a user gesture to construct/resume an AudioContext.
 * We unlock once on first document click, then reuse the context everywhere.
 */

let ctx: AudioContext | null = null;
let unlocked = false;

function ensureContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (ctx) return ctx;
  const Ctor =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return null;
  ctx = new Ctor();
  return ctx;
}

export function installAudioUnlock(): () => void {
  if (typeof document === "undefined") return () => undefined;
  const onClick = () => {
    const c = ensureContext();
    if (!c) return;
    if (c.state === "suspended") void c.resume();
    unlocked = true;
  };
  document.addEventListener("click", onClick, { once: true });
  return () => document.removeEventListener("click", onClick);
}

export function playTone(frequencyHz = 880, durationMs = 200): void {
  const c = ensureContext();
  if (!c || !unlocked) return;
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.type = "sine";
  osc.frequency.value = frequencyHz;
  gain.gain.value = 0.05;
  osc.connect(gain).connect(c.destination);
  osc.start();
  osc.stop(c.currentTime + durationMs / 1000);
}
