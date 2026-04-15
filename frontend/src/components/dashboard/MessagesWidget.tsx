import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { notes } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

interface Note {
  id: string;
  title: string;
  body: string;
  color: string;
  pinned: boolean;
  author_profile_id: string;
  created_at: string;
}

export default function MessagesWidget() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const profiles = useHouseholdStore((s) => s.profiles);
  const navigate = useNavigate();

  const { data: noteList = [] } = useQuery<Note[]>({
    queryKey: ["notes", householdId],
    queryFn: () => notes.getAll(householdId!).then((r) => r.data),
    enabled: !!householdId,
    staleTime: 2 * 60 * 1000,
  });

  // Show pinned first, then most recent, max 3
  const displayNotes = noteList.slice(0, 3);

  if (displayNotes.length === 0) return null;

  return (
    <section className="rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4">
      <button
        type="button"
        onClick={() => navigate("/messages")}
        className="flex items-center justify-between w-full mb-3 group"
      >
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          💬 Messages
        </h3>
        <span className="text-xs text-gray-400 group-hover:text-blue-500 transition-colors">
          View all →
        </span>
      </button>

      <div className="space-y-2">
        {displayNotes.map((note) => {
          const author = profiles.find((p) => p.id === note.author_profile_id);
          return (
            <div
              key={note.id}
              className="rounded-lg p-2.5 text-sm"
              style={{ backgroundColor: note.color + "20", borderLeft: `3px solid ${note.color}` }}
            >
              <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {note.pinned && "📌 "}{note.title}
              </div>
              {note.body && (
                <p className="text-xs text-gray-600 dark:text-gray-400 truncate mt-0.5">
                  {note.body}
                </p>
              )}
              <p className="text-xs text-gray-400 mt-1">
                {author?.avatar_emoji} {author?.display_name ?? "Unknown"}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
