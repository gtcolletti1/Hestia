import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { splash as splashApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useThemeStore } from "@/stores/themeStore";
import SplashContent from "./SplashContent";
import SplashPhotoLayer from "./SplashPhotoLayer";
import { KID_SAFE_PALETTE } from "./palette";
import type { SplashMode, SplashResponse } from "@/types/splash";

interface SplashViewProps {
  /** Called when the user touches/clicks anywhere — typically swaps
   *  the splash for the profile selector. */
  onUnlock: () => void;
  /** Admin-side preview override. When set, ignores the policy-derived
   *  ``splash_mode`` and runs the alternating cycle at a fixed
   *  fast-forward cadence (~10s/side per US-2.12.1a). */
  previewMode?: SplashMode;
  /** Suppresses the unlock-on-tap behaviour for the embedded admin
   *  preview frame (admins shouldn't be logged out by previewing). */
  disableUnlock?: boolean;
}

/** Modes we actually flip between when the admin chose "alternating". */
type DisplayedLayer = "ambient" | "photo";

/**
 * The pre-login wall display. Sits BEFORE the profile selector and
 * presents household information according to the admin's policy
 * (PRD §2.12). The backend enforces the policy server-side; this
 * component just renders whatever the server allowed.
 *
 * Modes:
 *  - ``ambient``     : always shows the data layer (clock, agenda, …).
 *  - ``photo``       : always shows the photo layer.
 *  - ``alternating`` : flips between the two on a configured interval,
 *                      pausing on touch (so a user can read the agenda
 *                      without it animating away mid-glance).
 */
export default function SplashView({ onUnlock, previewMode, disableUnlock }: SplashViewProps) {
  const householdId = useHouseholdStore((s) => s.householdId);
  const theme = useThemeStore((s) => s.theme);

  const { data, isLoading, error } = useQuery<SplashResponse>({
    queryKey: ["splash", householdId],
    queryFn: async () => {
      const res = await splashApi.get(householdId ?? undefined);
      return res.data;
    },
    refetchInterval: 30_000, // matches Cache-Control: max-age=30
    refetchOnWindowFocus: true,
    retry: 2,
  });

  const mode: SplashMode = previewMode ?? data?.policy.splash_mode ?? "ambient";
  const ambientSeconds = previewMode
    ? 10
    : data?.policy.splash_alternating_ambient_seconds ?? 60;
  const photoSeconds = previewMode
    ? 10
    : data?.policy.splash_alternating_photo_seconds ?? 60;

  const [displayed, setDisplayed] = useState<DisplayedLayer>(
    mode === "photo" ? "photo" : "ambient",
  );
  const [pausedUntil, setPausedUntil] = useState<number>(0);

  // Reset displayed layer when the admin changes mode at runtime.
  useEffect(() => {
    setDisplayed(mode === "photo" ? "photo" : "ambient");
  }, [mode]);

  // Alternation loop. Per US-2.12.1a, a touch interrupts the cycle and
  // pauses for ~10s so the user has time to read the screen before it
  // flips to the other layer. Each layer has its own dwell duration.
  useEffect(() => {
    if (mode !== "alternating") return;
    const dwell = (displayed === "ambient" ? ambientSeconds : photoSeconds) * 1000;
    const id = window.setTimeout(() => {
      if (Date.now() < pausedUntil) return;
      setDisplayed((d) => (d === "ambient" ? "photo" : "ambient"));
    }, Math.max(2000, dwell));
    return () => window.clearTimeout(id);
  }, [mode, displayed, ambientSeconds, photoSeconds, pausedUntil]);

  // The Hestia hearth is the default backdrop for every splash — both
  // the ambient data layer and the photo-frame layer sit on top of it
  // (the photo layer simply overlays its own image when one is loaded).
  // A dimming scrim guarantees text contrast on the bright fire.
  // CSS variables drive the kid-safe palette through Tailwind
  // arbitrary-value class references inside SplashContent.
  const styleVars = useMemo<React.CSSProperties>(() => {
    const dark = theme === "dark";
    return {
      "--splash-bg-start": dark ? KID_SAFE_PALETTE.bgStartDark : KID_SAFE_PALETTE.bgStart,
      "--splash-bg-end": dark ? KID_SAFE_PALETTE.bgEndDark : KID_SAFE_PALETTE.bgEnd,
      // Card surface — a translucent dark plate so light text is
      // readable on top of the warm hearth photo regardless of theme.
      "--splash-surface": "rgba(17,24,39,0.55)",
      "--splash-surface-strong": "rgba(17,24,39,0.72)",
      "--splash-border": "rgba(255,255,255,0.12)",
      // Always use light text — the hearth backdrop is dark/warm and
      // we don't want a light/dark theme flip to make text disappear
      // on the same photo.
      "--splash-text": KID_SAFE_PALETTE.textInverse,
      "--splash-text-muted": KID_SAFE_PALETTE.textInverseMuted,
    } as React.CSSProperties;
  }, [theme]);

  // ── Edge cases ─────────────────────────────────────────────────────
  // Treat any failure as "let the user proceed to sign-in" — the
  // splash is decorative; we must never strand a household member at
  // a blank screen because the server is sluggish.
  if (error || (!isLoading && !data)) {
    return (
      <FullbleedTapTarget onUnlock={onUnlock} disableUnlock={disableUnlock} style={styleVars}>
        <div className="flex h-full w-full items-center justify-center text-[color:var(--splash-text)]">
          <div className="text-center">
            <div className="text-2xl font-semibold">Hestia</div>
            <div className="mt-2 text-sm text-[color:var(--splash-text-muted)]">
              Tap to sign in
            </div>
          </div>
        </div>
      </FullbleedTapTarget>
    );
  }

  if (!data) {
    return (
      <FullbleedTapTarget onUnlock={onUnlock} disableUnlock={disableUnlock} style={styleVars}>
        <div className="flex h-full w-full items-center justify-center text-[color:var(--splash-text-muted)]">
          Loading…
        </div>
      </FullbleedTapTarget>
    );
  }

  return (
    <FullbleedTapTarget
      onUnlock={onUnlock}
      disableUnlock={disableUnlock}
      style={styleVars}
      onInteract={() => {
        // Pause alternation for 10s on touch (US-2.12.1a).
        setPausedUntil(Date.now() + 10_000);
      }}
    >
      {displayed === "photo" ? (
        <SplashPhotoLayer
          transitionSeconds={photoSeconds}
          timeFormat={data.clock.time_format}
        />
      ) : (
        <SplashContent data={data} timeFormat={data.clock.time_format} />
      )}
    </FullbleedTapTarget>
  );
}

interface TapTargetProps {
  onUnlock: () => void;
  onInteract?: () => void;
  disableUnlock?: boolean;
  style?: React.CSSProperties;
  children: React.ReactNode;
}

function FullbleedTapTarget({ onUnlock, onInteract, disableUnlock, style, children }: TapTargetProps) {
  const handlePress = (e: React.PointerEvent) => {
    onInteract?.();
    if (disableUnlock) return;
    if (e.button !== 0 || !e.isPrimary) return;
    onUnlock();
  };

  return (
    <div
      className={`${disableUnlock ? "absolute" : "fixed"} inset-0 z-40 cursor-pointer select-none overflow-hidden`}
      style={style}
      onPointerDown={handlePress}
      role="button"
      aria-label={disableUnlock ? "Splash preview" : "Tap to sign in"}
      tabIndex={0}
    >
      {/* Backdrop: the Hestia hearth fills every splash by default.
          Sub-layers (e.g. SplashPhotoLayer) can paint their own
          imagery on top of this. A linear-gradient scrim guarantees
          contrast at the edges where the fire is brightest. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage:
            "linear-gradient(160deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.25) 40%, rgba(0,0,0,0.55) 100%), url('/hestia-splash.png')",
        }}
      />
      <div className="relative h-full w-full">{children}</div>
    </div>
  );
}
