import { useState, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import client from "@/api/client";
import type { List, ListItem } from "./ListView";

interface Props {
  list: List;
  onClose: () => void;
  onEdit: () => void;
}

export default function ListDetail({ list, onClose, onEdit }: Props) {
  const queryClient = useQueryClient();
  const [newItemText, setNewItemText] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch live data
  const { data: liveList } = useQuery<List>({
    queryKey: ["list", list.id],
    queryFn: async () => (await client.get(`/lists/${list.id}`)).data,
    initialData: list,
  });

  const items = liveList.items;

  // Sort: unchecked first, then checked, maintaining sort_order within each group
  const sortedItems = [...items].sort((a, b) => {
    if (a.is_checked !== b.is_checked) return a.is_checked ? 1 : -1;
    return a.sort_order - b.sort_order;
  });

  const toggleItem = useMutation({
    mutationFn: (item: ListItem) =>
      client.patch(`/lists/${list.id}/items/${item.id}`, { is_checked: !item.is_checked }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["list", list.id] }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["lists"] }),
  });

  const addItem = useMutation({
    mutationFn: (text: string) =>
      client.post(`/lists/${list.id}/items`, { text }),
    onSuccess: () => {
      setNewItemText("");
      queryClient.invalidateQueries({ queryKey: ["list", list.id] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const deleteItem = useMutation({
    mutationFn: (itemId: string) => client.delete(`/lists/${list.id}/items/${itemId}`),
    onSuccess: () => {
      setDeletingId(null);
      queryClient.invalidateQueries({ queryKey: ["list", list.id] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const deleteList = useMutation({
    mutationFn: () => client.delete(`/lists/${list.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lists"] });
      onClose();
    },
  });

  const handleAddItem = (e: FormEvent) => {
    e.preventDefault();
    const text = newItemText.trim();
    if (!text) return;
    addItem.mutate(text);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] rounded-xl p-2 text-gray-600 hover:bg-gray-100 active:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-800"
            aria-label="Back"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-xl font-bold">{liveList.name}</h1>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="min-h-[44px] min-w-[44px] rounded-xl px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20"
          >
            Edit
          </button>
          <button
            onClick={() => {
              if (window.confirm("Delete this list?")) deleteList.mutate();
            }}
            className="min-h-[44px] min-w-[44px] rounded-xl px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto py-2">
        {sortedItems.length === 0 && (
          <p className="py-12 text-center text-gray-400 dark:text-gray-500">
            No items yet — add one below
          </p>
        )}

        <ul className="divide-y divide-gray-100 dark:divide-gray-800">
          {sortedItems.map((item) => (
            <li key={item.id} className="group relative">
              <div
                className={`flex items-center gap-3 px-2 py-3 transition ${
                  item.is_checked ? "opacity-60" : ""
                }`}
              >
                {/* Checkbox */}
                <button
                  onClick={() => toggleItem.mutate(item)}
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border-2 transition active:scale-90 ${
                    item.is_checked
                      ? "border-green-500 bg-green-500 text-white"
                      : "border-gray-300 hover:border-gray-400 dark:border-gray-600"
                  }`}
                  aria-label={item.is_checked ? "Uncheck item" : "Check item"}
                >
                  {item.is_checked && (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </button>

                {/* Content */}
                <div className="flex-1">
                  <span
                    className={`text-base ${
                      item.is_checked ? "text-gray-400 line-through dark:text-gray-500" : ""
                    }`}
                  >
                    {item.text}
                  </span>
                  <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                    {item.profile_name && (
                      <span className="rounded-full bg-purple-100 px-2 py-0.5 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                        {item.profile_name}
                      </span>
                    )}
                    {item.due_date && <span>Due {format(new Date(item.due_date), "MMM d")}</span>}
                  </div>
                </div>

                {/* Delete */}
                {deletingId === item.id ? (
                  <button
                    onClick={() => deleteItem.mutate(item.id)}
                    className="min-h-[44px] min-w-[44px] rounded-xl bg-red-600 px-3 py-2 text-sm font-medium text-white active:scale-95"
                  >
                    Confirm
                  </button>
                ) : (
                  <button
                    onClick={() => setDeletingId(item.id)}
                    className="min-h-[44px] min-w-[44px] rounded-xl p-2 text-gray-400 opacity-0 transition hover:text-red-500 group-hover:opacity-100"
                    aria-label="Delete item"
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* Quick-add input — always visible at bottom */}
      <form
        onSubmit={handleAddItem}
        className="flex gap-2 border-t border-gray-200 pt-3 dark:border-gray-700"
      >
        <input
          type="text"
          value={newItemText}
          onChange={(e) => setNewItemText(e.target.value)}
          placeholder="Add an item…"
          className="min-h-[48px] flex-1 rounded-xl border border-gray-300 px-4 text-base focus:border-blue-500 focus:ring-2 focus:ring-blue-200 dark:border-gray-600 dark:bg-gray-800 dark:focus:ring-blue-800"
        />
        <button
          type="submit"
          disabled={addItem.isPending || !newItemText.trim()}
          className="min-h-[48px] min-w-[48px] rounded-xl bg-blue-600 px-5 font-semibold text-white shadow hover:bg-blue-700 disabled:opacity-50 active:scale-95 transition"
        >
          Add
        </button>
      </form>
    </div>
  );
}
