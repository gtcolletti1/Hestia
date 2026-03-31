import { useEffect, useRef, useCallback, type ReactNode } from "react";

interface KioskWrapperProps {
  children: ReactNode;
}

const IDLE_TIMEOUT_MS = 5000;

export default function KioskWrapper({ children }: KioskWrapperProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  const showCursor = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.style.cursor = "default";
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (el) el.style.cursor = "none";
    }, IDLE_TIMEOUT_MS);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Prevent right-click context menu
    const preventContext = (e: MouseEvent) => e.preventDefault();
    el.addEventListener("contextmenu", preventContext);

    // Start idle timer
    timerRef.current = setTimeout(() => {
      if (el) el.style.cursor = "none";
    }, IDLE_TIMEOUT_MS);

    // Reset cursor on any pointer activity
    el.addEventListener("mousemove", showCursor);
    el.addEventListener("touchstart", showCursor);

    return () => {
      el.removeEventListener("contextmenu", preventContext);
      el.removeEventListener("mousemove", showCursor);
      el.removeEventListener("touchstart", showCursor);
      clearTimeout(timerRef.current);
    };
  }, [showCursor]);

  return (
    <div ref={containerRef} className="kiosk-wrapper h-screen w-screen">
      {children}
    </div>
  );
}
