import { useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { admin } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import ScreensaverOverlay from "./ScreensaverOverlay";

interface KioskWrapperProps {
  children: ReactNode;
}

const CURSOR_HIDE_MS = 5000;

export default function KioskWrapper({ children }: KioskWrapperProps) {
  const householdId = useHouseholdStore((s) => s.householdId);
  const cursorTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const screensaverTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [screensaverActive, setScreensaverActive] = useState(false);

  const { data: settings } = useQuery({
    queryKey: ["settings", householdId],
    queryFn: () => admin.getSettings(householdId!).then((r) => r.data as {
      screensaver_timeout_minutes?: number;
      screensaver_transition_seconds?: number;
    }),
    enabled: !!householdId,
    staleTime: 60_000,
  });

  const timeoutMs = (settings?.screensaver_timeout_minutes ?? 2) * 60 * 1000;
  const transitionSeconds = settings?.screensaver_transition_seconds ?? 10;

  const resetTimers = useCallback(() => {
    const el = containerRef.current;

    // Cursor: show for 5s then hide
    if (el) el.style.cursor = "default";
    clearTimeout(cursorTimerRef.current);
    cursorTimerRef.current = setTimeout(() => {
      if (el) el.style.cursor = "none";
    }, CURSOR_HIDE_MS);

    // Screensaver: activate after configured idle time
    clearTimeout(screensaverTimerRef.current);
    screensaverTimerRef.current = setTimeout(() => {
      setScreensaverActive(true);
    }, timeoutMs);
  }, [timeoutMs]);

  const dismissScreensaver = useCallback(() => {
    setScreensaverActive(false);
    resetTimers();
  }, [resetTimers]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const preventContext = (e: MouseEvent) => e.preventDefault();
    el.addEventListener("contextmenu", preventContext);

    // Start timers
    resetTimers();

    // Reset on any activity
    el.addEventListener("mousemove", resetTimers);
    el.addEventListener("touchstart", resetTimers);
    el.addEventListener("keydown", resetTimers);

    return () => {
      el.removeEventListener("contextmenu", preventContext);
      el.removeEventListener("mousemove", resetTimers);
      el.removeEventListener("touchstart", resetTimers);
      el.removeEventListener("keydown", resetTimers);
      clearTimeout(cursorTimerRef.current);
      clearTimeout(screensaverTimerRef.current);
    };
  }, [resetTimers]);

  return (
    <div ref={containerRef} className="kiosk-wrapper h-screen w-screen">
      {children}
      {screensaverActive && (
        <ScreensaverOverlay
          onDismiss={dismissScreensaver}
          transitionSeconds={transitionSeconds}
        />
      )}
    </div>
  );
}
