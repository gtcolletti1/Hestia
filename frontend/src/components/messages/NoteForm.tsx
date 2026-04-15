import { useState } from "react";
import type { NoteFormData } from "./MessageBoard";

interface NoteFormProps {
  colors: string[];
  initial?: { title: string; body: string; color: string; pinned: boolean };
  onSubmit: (data: NoteFormData) => void;
  onCancel: () => void;
  isPending: boolean;
}

export default function NoteForm({ colors, initial, onSubmit, onCancel, isPending }: NoteFormProps) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [body, setBody] = useState(initial?.body ?? "");
  const [color, setColor] = useState(initial?.color ?? colors[0]);
  const [pinned, setPinned] = useState(initial?.pinned ?? false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({ title: title.trim(), body: body.trim(), color, pinned });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800 p-6 shadow-xl space-y-4"
      >
        <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
          {initial ? "Edit Note" : "New Note"}
        </h2>

        <input
          type="text"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2.5 text-base text-gray-900 dark:text-gray-100"
          autoFocus
        />

        <textarea
          placeholder="Write your message…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 resize-none"
        />

        {/* Color picker */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
            Color
          </label>
          <div className="flex gap-2">
            {colors.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`h-8 w-8 rounded-full border-2 transition-transform ${
                  color === c ? "border-gray-900 dark:border-white scale-110" : "border-transparent"
                }`}
                style={{ backgroundColor: c }}
                aria-label={`Color ${c}`}
              />
            ))}
          </div>
        </div>

        {/* Pin toggle */}
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={pinned}
            onChange={(e) => setPinned(e.target.checked)}
            className="rounded"
          />
          📌 Pin to top
        </label>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border border-gray-300 dark:border-gray-600 px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 min-h-[44px]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim() || isPending}
            className="flex-1 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 min-h-[44px]"
          >
            {isPending ? "Saving…" : initial ? "Update" : "Post"}
          </button>
        </div>
      </form>
    </div>
  );
}
