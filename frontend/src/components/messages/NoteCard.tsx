import { useHouseholdStore } from "@/stores/householdStore";
import type { Note } from "./MessageBoard";

interface NoteCardProps {
  note: Note;
  onEdit: () => void;
  onDelete: () => void;
  onTogglePin: () => void;
}

export default function NoteCard({ note, onEdit, onDelete, onTogglePin }: NoteCardProps) {
  const profiles = useHouseholdStore((s) => s.profiles);
  const author = profiles.find((p) => p.id === note.author_profile_id);

  const timeAgo = getTimeAgo(note.created_at);

  return (
    <div
      className="rounded-2xl p-4 shadow-sm border border-black/5 flex flex-col gap-2 min-h-[140px] transition-transform hover:scale-[1.01]"
      style={{ backgroundColor: note.color + "30", borderLeft: `4px solid ${note.color}` }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-base leading-snug flex-1">
          {note.pinned && <span className="mr-1">📌</span>}
          {note.title}
        </h3>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            type="button"
            onClick={onTogglePin}
            className="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs"
            title={note.pinned ? "Unpin" : "Pin"}
          >
            {note.pinned ? "📌" : "📍"}
          </button>
          <button
            type="button"
            onClick={onEdit}
            className="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs"
            title="Edit"
          >
            ✏️
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="p-1 rounded text-gray-400 hover:text-red-500 text-xs"
            title="Delete"
          >
            🗑️
          </button>
        </div>
      </div>

      {/* Body */}
      {note.body && (
        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap line-clamp-4 flex-1">
          {note.body}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mt-auto pt-1">
        <span className="flex items-center gap-1">
          {author?.avatar_emoji && <span>{author.avatar_emoji}</span>}
          {author?.display_name ?? "Unknown"}
        </span>
        <span>{timeAgo}</span>
      </div>
    </div>
  );
}

function getTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}
