import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import client from "@/api/client";
import LoadingSpinner from "@/components/shared/LoadingSpinner";
import EmptyState from "@/components/shared/EmptyState";
import Modal from "@/components/shared/Modal";
import ListDetail from "./ListDetail";
import ListForm from "./ListForm";

// ── Local types (no shared @/types yet) ──

export interface ListItem {
  id: string;
  text: string;
  is_checked: boolean;
  sort_order: number;
  profile_id?: string;
  profile_name?: string;
  due_date?: string;
}

export interface List {
  id: string;
  name: string;
  icon?: string;
  category: string;
  items: ListItem[];
}

export const LIST_CATEGORIES = [
  { value: "all", label: "All", icon: "📋" },
  { value: "grocery", label: "Grocery", icon: "🛒" },
  { value: "todo", label: "To-Do", icon: "✅" },
  { value: "packing", label: "Packing", icon: "🧳" },
  { value: "shopping", label: "Shopping", icon: "🛍️" },
  { value: "chores", label: "Chores", icon: "🧹" },
  { value: "other", label: "Other", icon: "📝" },
] as const;

export default function ListView() {
  const queryClient = useQueryClient();
  const [activeCategory, setActiveCategory] = useState("all");
  const [selectedListId, setSelectedListId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingList, setEditingList] = useState<List | null>(null);

  const {
    data: lists = [],
    isLoading,
    error,
  } = useQuery<List[]>({
    queryKey: ["lists"],
    queryFn: async () => (await client.get("/lists")).data,
  });

  const filteredLists =
    activeCategory === "all"
      ? lists
      : lists.filter((l) => l.category === activeCategory);

  const selectedList = lists.find((l) => l.id === selectedListId) ?? null;

  // ── Drill-in to a list ──
  if (selectedList) {
    return (
      <ListDetail
        list={selectedList}
        onClose={() => setSelectedListId(null)}
        onEdit={() => {
          setEditingList(selectedList);
          setSelectedListId(null);
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <h1 className="text-2xl font-bold">Lists</h1>

      {/* Category filter tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {LIST_CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setActiveCategory(cat.value)}
            className={`flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition active:scale-95 ${
              activeCategory === cat.value
                ? "bg-blue-600 text-white shadow"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            }`}
          >
            <span>{cat.icon}</span> {cat.label}
          </button>
        ))}
      </div>

      {isLoading && <LoadingSpinner message="Loading lists…" />}

      {error && (
        <div className="rounded-xl bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Failed to load lists. Please try again.
        </div>
      )}

      {/* List cards grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filteredLists.map((list) => {
          const total = list.items.length;
          const checked = list.items.filter((i) => i.is_checked).length;
          const pct = total > 0 ? (checked / total) * 100 : 0;

          return (
            <button
              key={list.id}
              onClick={() => setSelectedListId(list.id)}
              className="flex flex-col rounded-2xl border-2 border-gray-200 bg-white p-4 text-left shadow-sm transition hover:shadow-md active:scale-[0.98] dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{list.icon || "📋"}</span>
                  <h3 className="text-base font-semibold">{list.name}</h3>
                </div>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                  {LIST_CATEGORIES.find((c) => c.value === list.category)
                    ?.label ?? list.category}
                </span>
              </div>

              {/* Progress */}
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>
                    {checked}/{total} items
                  </span>
                  <span>{Math.round(pct)}%</span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    className="h-full rounded-full bg-green-500 transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {!isLoading && filteredLists.length === 0 && (
        <EmptyState
          icon="📝"
          title="No lists yet"
          description="Tap the + button to create one"
          action={{ label: "New List", onClick: () => setShowForm(true) }}
        />
      )}

      {/* FAB — New List */}
      <button
        onClick={() => setShowForm(true)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-2xl text-white shadow-lg transition hover:bg-blue-700 active:scale-90"
        aria-label="New list"
      >
        +
      </button>

      {/* Create / Edit modal */}
      <Modal
        open={showForm || !!editingList}
        onClose={() => {
          setShowForm(false);
          setEditingList(null);
        }}
        title={editingList ? "Edit List" : "New List"}
      >
        <ListForm
          list={editingList ?? undefined}
          onClose={() => {
            setShowForm(false);
            setEditingList(null);
          }}
          onSaved={() => {
            setShowForm(false);
            setEditingList(null);
            queryClient.invalidateQueries({ queryKey: ["lists"] });
          }}
        />
      </Modal>
    </div>
  );
}
