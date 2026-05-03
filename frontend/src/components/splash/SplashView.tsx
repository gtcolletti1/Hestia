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
export default function SplashView({ onUnlock }: SplashViewProps) {
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

  const mode: SplashMode = data?.policy.splash_mode ?? "ambient";
  const altSeconds = data?.policy.splash_alternating_seconds ?? 30;

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
  // flips to the other layer.
  useEffect(() => {
    if (mode !== "alternating") return;
    const id = window.setInterval(() => {
      if (Date.now() < pausedUntil) return;
      setDisplayed((d) => (d === "ambient" ? "photo" : "ambient"));
    }, Math.max(5, altSeconds) * 1000);
    return () => window.clearInterval(id);
  }, [mode, altSeconds, pausedUntil]);

  // CSS variables drive the kid-safe palette through Tailwind
  // arbitrary-value class references inside SplashContent (e.g.
  // `text-[color:var(--splash-text)]`), so theme changes don't
  // require a re-render of every coloured node.
  const styleVars = useMemo<React.CSSProperties>(() => {
    const dark = theme === "dark";
    return {
      "--splash-bg-start": dark ? KID_SAFE_PALETTE.bgStartDark : KID_SAFE_PALETTE.bgStart,
      "--splash-bg-end": dark ? KID_SAFE_PALETTE.bgEndDark : KID_SAFE_PALETTE.bgEnd,
      "--splash-surface": dark ? KID_SAFE_PALETTE.surfaceDark : KID_SAFE_PALETTE.surface,
      "--splash-text": dark ? KID_SAFE_PALETTE.textInverse : KID_SAFE_PALETTE.text,
      "--splash-text-muted": dark
        ? KID_SAFE_PALETTE.textInverseMuted
        : KID_SAFE_PALETTE.textMuted,
      background: `linear-gradient(135deg, var(--splash-bg-start), var(--splash-bg-end))`,
    } as React.CSSProperties;
  }, [theme]);

  // ── Edge cases ─────────────────────────────────────────────────────
  // Treat any failure as "let the user proceed to sign-in" — the
  // splash is decorative; we must never strand a household member at
  // a blank screen because the server is sluggish.
  if (error || (!isLoading && !data)) {
    return (
      <FullbleedTapTarget onUnlock={onUnlock} style={styleVars}>
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
      <FullbleedTapTarget onUnlock={onUnlock} style={styleVars}>
        <div className="flex h-full w-full items-center justify-center text-[color:var(--splash-text-muted)]">
          Loading…
        </div>
      </FullbleedTapTarget>
    );
  }

  return (
    <FullbleedTapTarget
      onUnlock={onUnlock}
      style={styleVars}
      onInteract={() => {
        // Pause alternation for 10s on touch (US-2.12.1a).
        setPausedUntil(Date.now() + 10_000);
      }}
    >
      {displayed === "photo" ? (
        <SplashPhotoLayer
          transitionSeconds={altSeconds}
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
  style?: React.CSSProperties;
  children: React.ReactNode;
}

function FullbleedTapTarget({ onUnlock, onInteract, style, children }: TapTargetProps) {
  // The whole splash is one big button. Pressing anywhere takes the
  // user to the profile selector. We use ``onPointerDown`` so the
  // transition feels instant (fires before click on touch devices).
  const handlePress = (e: React.PointerEvent) => {
    onInteract?.();
    // Right-click and synthesized pointer events from screensaver
    // dismissal should not log anyone in — only primary, isPrimary
    // user gestures unlock.
    if (e.button !== 0 || !e.isPrimary) return;
    onUnlock();
  };

  return (
    <div
      className="fixed inset-0 z-40 cursor-pointer select-none overflow-hidden"
      style={style}
      onPointerDown={handlePress}
      role="button"
      aria-label="Tap to sign in"
      tabIndex={0}
    >
      {children}
    </div>
  );
}
