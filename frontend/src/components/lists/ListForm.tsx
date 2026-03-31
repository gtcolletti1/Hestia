import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import client from "@/api/client";
import type { List } from "./ListView";

const CATEGORY_OPTIONS = [
  { value: "grocery", label: "Grocery", icon: "🛒" },
  { value: "todo", label: "To-Do", icon: "✅" },
  { value: "packing", label: "Packing", icon: "🧳" },
  { value: "shopping", label: "Shopping", icon: "🛍️" },
  { value: "chores", label: "Chores", icon: "🧹" },
  { value: "other", label: "Other", icon: "📝" },
];

const ICON_OPTIONS = [
  "📋", "🛒", "✅", "🧳", "🛍️", "🧹",
  "📝", "🎒", "🏠", "💊", "📚", "🎁",
];

interface Props {
  list?: List;
  onClose: () => void;
  onSaved: () => void;
}

export default function ListForm({ list, onClose, onSaved }: Props) {
  const queryClient = useQueryClient();
  const isEditing = !!list;

  const [name, setName] = useState(list?.name ?? "");
  const [category, setCategory] = useState(list?.category ?? "todo");
  const [icon, setIcon] = useState(list?.icon ?? "📋");

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (isEditing) {
        return client.put(`/lists/${list.id}`, payload);
      }
      return client.post("/lists", payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] });
      onSaved();
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    saveMutation.mutate({ name: name.trim(), category, icon });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name */}
      <div>
        <label htmlFor="list-name" className="mb-1 block text-sm font-medium">
          List Name
        </label>
        <input
          id="list-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Weekly Groceries"
          required
          className="touch-target w-full rounded-xl border border-gray-300 px-4 py-2 text-base focus:border-blue-500 focus:ring-2 focus:ring-blue-200 dark:border-gray-600 dark:bg-gray-800 dark:focus:ring-blue-800"
        />
      </div>

      {/* Category */}
      <div>
        <span className="mb-2 block text-sm font-medium">Category</span>
        <div className="grid grid-cols-3 gap-2">
          {CATEGORY_OPTIONS.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setCategory(cat.value)}
              className={`flex min-h-[48px] flex-col items-center justify-center gap-1 rounded-xl border-2 px-2 py-3 text-sm font-medium transition active:scale-95 ${
                category === cat.value
                  ? "border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800"
              }`}
            >
              <span className="text-xl">{cat.icon}</span>
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Icon picker */}
      <div>
        <span className="mb-2 block text-sm font-medium">
          Icon <span className="text-gray-400">(optional)</span>
        </span>
        <div className="flex flex-wrap gap-2">
          {ICON_OPTIONS.map((ic) => (
            <button
              key={ic}
              type="button"
              onClick={() => setIcon(ic)}
              className={`flex h-12 w-12 items-center justify-center rounded-xl border-2 text-xl transition active:scale-95 ${
                icon === ic
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
                  : "border-gray-200 hover:border-gray-300 dark:border-gray-700"
              }`}
            >
              {ic}
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onClose}
          className="min-h-[48px] flex-1 rounded-xl border border-gray-300 py-3 font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saveMutation.isPending || !name.trim()}
          className="min-h-[48px] flex-1 rounded-xl bg-blue-600 py-3 font-semibold text-white shadow hover:bg-blue-700 disabled:opacity-50"
        >
          {saveMutation.isPending
            ? "Saving…"
            : isEditing
              ? "Update"
              : "Create"}
        </button>
      </div>

      {saveMutation.isError && (
        <p className="text-center text-sm text-red-600 dark:text-red-400">
          Failed to save list. Please try again.
        </p>
      )}
    </form>
  );
}
