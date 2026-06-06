"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getFoodByBarcode, type FoodResponse } from "@/lib/api/nutrition";

interface Props {
  /** Called when a barcode resolves to a food. */
  onFound: (food: FoodResponse) => void;
}

type Status = "idle" | "starting" | "scanning" | "looking-up" | "denied" | "not-found" | "error";

export function BarcodeScanner({ onFound }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const lookingUpRef = useRef(false);
  const [status, setStatus] = useState<Status>("idle");
  const [lastCode, setLastCode] = useState<string | null>(null);

  const stop = () => {
    controlsRef.current?.stop();
    controlsRef.current = null;
  };

  // Clean up the camera when the component unmounts.
  useEffect(() => () => stop(), []);

  const start = async () => {
    setStatus("starting");
    setLastCode(null);
    try {
      // Lazy-load zxing so it isn't in the main bundle.
      const { BrowserMultiFormatReader } = await import("@zxing/browser");
      const reader = new BrowserMultiFormatReader();
      if (!videoRef.current) return;
      setStatus("scanning");
      controlsRef.current = await reader.decodeFromVideoDevice(
        undefined, // default camera (browser picks the rear on mobile)
        videoRef.current,
        async (result) => {
          if (!result || lookingUpRef.current) return;
          const code = result.getText();
          lookingUpRef.current = true;
          setLastCode(code);
          setStatus("looking-up");
          try {
            const food = await getFoodByBarcode(code);
            stop();
            onFound(food);
          } catch (e) {
            const status = (e as { status?: number })?.status;
            if (status === 404) {
              setStatus("not-found");
            } else {
              setStatus("error");
            }
            // Allow another scan after a short cooldown.
            window.setTimeout(() => {
              lookingUpRef.current = false;
              if (controlsRef.current) setStatus("scanning");
            }, 1500);
          }
        },
      );
    } catch (e) {
      const name = (e as { name?: string })?.name;
      setStatus(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "error");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {status === "idle" ? (
        <div className="border-border-strong rounded-[var(--radius-card)] border border-dashed p-6 text-center">
          <Camera className="text-text-tertiary mx-auto h-7 w-7" aria-hidden />
          <p className="text-text-secondary mt-2 text-sm">
            Scan a product barcode to look it up automatically.
          </p>
          <Button size="sm" className="mt-3" onClick={start}>
            Start camera
          </Button>
        </div>
      ) : null}

      {status === "denied" ? (
        <div className="border-destructive/40 bg-destructive-soft rounded-[var(--radius-card)] border p-4 text-center">
          <p className="text-text text-sm font-medium">Camera permission denied</p>
          <p className="text-text-secondary mt-1 text-xs">
            Allow camera access in your browser settings, then try again. You can also search by
            name instead.
          </p>
          <Button size="sm" variant="secondary" className="mt-3" onClick={start}>
            Retry
          </Button>
        </div>
      ) : null}

      {/* Live camera view (kept mounted while scanning/looking-up) */}
      {status === "starting" ||
      status === "scanning" ||
      status === "looking-up" ||
      status === "not-found" ||
      status === "error" ? (
        <div className="relative">
          <video
            ref={videoRef}
            className="bg-surface-sunken aspect-[4/3] w-full rounded-[var(--radius-card)] object-cover"
            muted
            playsInline
          />
          {/* aiming guide */}
          <div className="border-accent pointer-events-none absolute inset-x-8 top-1/2 h-0.5 -translate-y-1/2 border-t-2 opacity-70" />
          <div className="absolute inset-x-0 bottom-2 flex flex-col items-center gap-1">
            {status === "looking-up" ? (
              <span className="bg-overlay text-text-inverse inline-flex items-center gap-1.5 rounded-[var(--radius-pill)] px-3 py-1 text-xs">
                <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> Looking up {lastCode}…
              </span>
            ) : status === "not-found" ? (
              <span className="bg-overlay text-text-inverse rounded-[var(--radius-pill)] px-3 py-1 text-xs">
                {lastCode} not found — try search
              </span>
            ) : status === "error" ? (
              <span className="bg-overlay text-text-inverse rounded-[var(--radius-pill)] px-3 py-1 text-xs">
                Lookup failed — keep scanning
              </span>
            ) : (
              <span className="bg-overlay text-text-inverse rounded-[var(--radius-pill)] px-3 py-1 text-xs">
                Point at a barcode
              </span>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
