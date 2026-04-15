import { useEffect, useRef, useState, useCallback } from "react";
import { notifications as notificationsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

export interface NotificationItem {
  reminder_id: string;
  event_id: string;
  event_title: string;
  event_start: string;
  minutes_before: number;
  fire_at: string;
}

const POLL_INTERVAL_MS = 30_000; // 30 seconds

export function useNotifications() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const [toasts, setToasts] = useState<NotificationItem[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const dismissToast = useCallback((reminderId: string) => {
    setToasts((prev) => prev.filter((t) => t.reminder_id !== reminderId));
  }, []);

  useEffect(() => {
    if (!householdId) return;

    const poll = async () => {
      try {
        const { data } = await notificationsApi.getUpcoming(householdId);
        if (data.length > 0) {
          setToasts((prev) => {
            const existing = new Set(prev.map((t) => t.reminder_id));
            const newOnes = data.filter((n: NotificationItem) => !existing.has(n.reminder_id));
            return [...prev, ...newOnes];
          });

          // Browser notification
          if (Notification.permission === "granted") {
            for (const n of data as NotificationItem[]) {
              new Notification(`🔔 ${n.event_title}`, {
                body: `Starting in ${n.minutes_before} minutes`,
                icon: "/favicon.ico",
              });
            }
          }
        }
      } catch {
        // silently ignore poll errors
      }
    };

    poll(); // initial
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => clearInterval(intervalRef.current);
  }, [householdId]);

  const requestPermission = useCallback(async () => {
    if ("Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
  }, []);

  return { toasts, dismissToast, requestPermission };
}
