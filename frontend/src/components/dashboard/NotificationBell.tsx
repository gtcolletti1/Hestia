import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { formatDistanceToNow, parseISO } from "date-fns";
import { notifications as notificationsApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

interface InboxEntry {
  id: string;
  household_id: string;
  profile_id: string | null;
  kind: string;
  title: string;
  body: string | null;
  link_url: string | null;
  created_at: string;
  read_at: string | null;
}

const POLL_MS = 30_000;

const KIND_ICON: Record<string, string> = {
  reminder: "⏰",
  sync_error: "⚠️",
  info: "ℹ️",
};

export default function NotificationBell() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const countQuery = useQuery({
    queryKey: ["notifications-unread-count", householdId],
    queryFn: async () => {
      const { data } = await notificationsApi.inboxUnreadCount(householdId!);
      return data.unread as number;
    },
    enabled: !!householdId,
    refetchInterval: POLL_MS,
  });

  const inboxQuery = useQuery({
    queryKey: ["notifications-inbox", householdId],
    queryFn: async () => {
      const { data } = await notificationsApi.inbox(householdId!, { limit: 20 });
      return data as InboxEntry[];
    },
    enabled: !!householdId && open,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.inboxMarkRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-inbox", householdId] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread-count", householdId] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.inboxMarkAllRead(householdId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-inbox", householdId] });
      queryClient.invalidateQueries({ queryKey: ["notifications-unread-count", householdId] });
    },
  });

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const unread = countQuery.data ?? 0;
  const entries = inboxQuery.data ?? [];

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="relative inline-flex h-11 w-11 items-center justify-center rounded-full bg-white text-gray-600 shadow-sm hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
        aria-label={`Notifications${unread > 0 ? ` (${unread} unread)` : ""}`}
      >
        <span className="text-xl" aria-hidden>🔔</span>
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 inline-flex min-w-[20px] items-center justify-center rounded-full bg-red-500 px-1 text-[11px] font-semibold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 max-w-[90vw] rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2 dark:border-gray-700">
            <h3 className="text-sm font-semibold">Notifications</h3>
            {unread > 0 && (
              <button
                type="button"
                onClick={() => markAllReadMutation.mutate()}
                className="text-xs text-blue-600 hover:underline dark:text-blue-400"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {inboxQuery.isLoading ? (
              <p className="p-4 text-sm text-gray-500">Loading…</p>
            ) : entries.length === 0 ? (
              <p className="p-4 text-sm text-gray-500">You're all caught up.</p>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                {entries.map((e) => {
                  const isUnread = e.read_at === null;
                  return (
                    <li
                      key={e.id}
                      className={`flex gap-3 px-4 py-3 ${
                        isUnread ? "bg-blue-50/60 dark:bg-blue-900/20" : ""
                      }`}
                    >
                      <span className="text-lg leading-none" aria-hidden>
                        {KIND_ICON[e.kind] ?? "•"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{e.title}</p>
                        {e.body && (
                          <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                            {e.body}
                          </p>
                        )}
                        <p className="mt-0.5 text-[11px] text-gray-400">
                          {formatDistanceToNow(parseISO(e.created_at), {
                            addSuffix: true,
                          })}
                        </p>
                      </div>
                      {isUnread && (
                        <button
                          type="button"
                          onClick={() => markReadMutation.mutate(e.id)}
                          className="self-start text-[11px] text-blue-600 hover:underline dark:text-blue-400"
                          aria-label="Mark as read"
                        >
                          ✓
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
