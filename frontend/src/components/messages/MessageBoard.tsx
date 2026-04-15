import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notes } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import NoteCard from "./NoteCard";
import NoteForm from "./NoteForm";

export interface Note {
  id: string;
  household_id: string;
  author_profile_id: string;
  title: string;
  body: string;
  color: string;
  pinned: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export type NoteFormData = {
  title: string;
  body: string;
  color: string;
  pinned: boolean;
};

const NOTE_COLORS = [
  "#FBBF24", // amber
  "#34D399", // emerald
  "#60A5FA", // blue
  "#F472B6", // pink
  "#A78BFA", // violet
  "#FB923C", // orange
  "#2DD4BF", // teal
  "#F87171", // red
];

export default function MessageBoard() {
  const householdId = useHouseholdStore((s) => s.householdId);
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingNote, setEditingNote] = useState<Note | null>(null);

  const { data: noteList = [], isLoading } = useQuery<Note[]>({
    queryKey: ["notes", householdId],
    queryFn: () => notes.getAll(householdId!).then((r) => r.data),
    enabled: !!householdId,
  });

  const createMutation = useMutation({
    mutationFn: (data: NoteFormData) =>
      notes.create({ ...data, household_id: householdId! }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<NoteFormData> }) =>
      notes.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setEditingNote(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => notes.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notes"] }),
  });

  const togglePin = (note: Note) => {
    updateMutation.mutate({ id: note.id, data: { pinned: !note.pinned } });
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          💬 Message Board
        </h1>
        <button
          type="button"
          onClick={() => {
            setEditingNote(null);
            setShowForm(true);
          }}
          className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 active:bg-blue-800 min-h-[44px]"
        >
          + New Note
        </button>
      </div>

      {/* Form modal */}
      {(showForm || editingNote) && (
        <NoteForm
          colors={NOTE_COLORS}
          initial={editingNote ?? undefined}
          onSubmit={(data) => {
            if (editingNote) {
              updateMutation.mutate({ id: editingNote.id, data });
            } else {
              createMutation.mutate(data);
            }
          }}
          onCancel={() => {
            setShowForm(false);
            setEditingNote(null);
          }}
          isPending={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Notes grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-40 rounded-2xl bg-gray-200 dark:bg-gray-700 animate-pulse"
            />
          ))}
        </div>
      ) : noteList.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-5xl mb-3">📝</p>
          <p className="text-lg font-medium">No notes yet</p>
          <p className="text-sm mt-1">Post a note for the family!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {noteList.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              onEdit={() => setEditingNote(note)}
              onDelete={() => deleteMutation.mutate(note.id)}
              onTogglePin={() => togglePin(note)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
