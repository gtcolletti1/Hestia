import type { NotificationItem } from "@/hooks/useNotifications";
import { format, parseISO } from "date-fns";

interface NotificationToastProps {
  toasts: NotificationItem[];
  onDismiss: (reminderId: string) => void;
}

export default function NotificationToast({ toasts, onDismiss }: NotificationToastProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.reminder_id}
          className="rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4 shadow-lg animate-slide-in flex items-start gap-3"
        >
          <span className="text-2xl flex-shrink-0">🔔</span>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm truncate">
              {toast.event_title}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Starts at {format(parseISO(toast.event_start), "h:mm a")}
              {" · "}
              {toast.minutes_before}min reminder
            </p>
          </div>
          <button
            type="button"
            onClick={() => onDismiss(toast.reminder_id)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-sm p-1 flex-shrink-0"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        .animate-slide-in {
          animation: slideIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
