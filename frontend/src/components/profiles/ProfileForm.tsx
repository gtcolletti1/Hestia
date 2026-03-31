import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { profiles } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import type { Profile } from "@/types";

const PRESET_COLORS = [
  "#EF4444",
  "#F97316",
  "#EAB308",
  "#22C55E",
  "#14B8A6",
  "#06B6D4",
  "#3B82F6",
  "#6366F1",
  "#8B5CF6",
  "#A855F7",
  "#EC4899",
  "#F43F5E",
  "#78716C",
  "#64748B",
  "#0EA5E9",
  "#10B981",
];

const ROLES: { value: Profile["role"]; label: string }[] = [
  { value: "admin", label: "Admin" },
  { value: "standard", label: "Standard" },
  { value: "kid", label: "Kid" },
];

interface ProfileFormProps {
  profile?: Profile;
  onClose: () => void;
  onSaved: () => void;
}

export default function ProfileForm({
  profile,
  onClose,
  onSaved,
}: ProfileFormProps) {
  const householdId = useHouseholdStore((s) => s.householdId)!;
  const queryClient = useQueryClient();
  const isEditing = !!profile;

  const [name, setName] = useState(profile?.name || "");
  const [role, setRole] = useState<Profile["role"]>(
    profile?.role || "standard",
  );
  const [color, setColor] = useState(profile?.color || PRESET_COLORS[0]);
  const [avatarUrl, setAvatarUrl] = useState(profile?.avatar_url || "");
  const [pin, setPin] = useState("");
  const [isActive, setIsActive] = useState(profile?.is_active ?? true);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["profiles"] });
    onSaved();
  };

  const createMutation = useMutation({
    mutationFn: (data: Partial<Profile>) =>
      profiles.create(householdId, data),
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Profile>) =>
      profiles.update(householdId, profile!.id, data),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: () => profiles.delete(householdId, profile!.id),
    onSuccess: invalidate,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Partial<Profile> & { pin?: string } = {
      name: name.trim(),
      role,
      color,
      avatar_url: avatarUrl.trim() || undefined,
      is_active: isActive,
      ...(pin ? { pin } : {}),
    };

    if (isEditing) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-800 shadow-xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            {isEditing ? "Edit Profile" : "Add Profile"}
          </h2>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Family member name"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
              required
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Role
            </label>
            <div className="grid grid-cols-3 gap-2">
              {ROLES.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setRole(r.value)}
                  className={`rounded-xl py-3 px-4 text-sm font-medium min-h-[44px] transition-colors ${
                    role === r.value
                      ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {/* Color picker */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Color
            </label>
            <div className="grid grid-cols-8 gap-2">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-10 w-10 rounded-full min-h-[44px] min-w-[44px] transition-transform ${
                    color === c
                      ? "ring-2 ring-offset-2 ring-blue-500 scale-110"
                      : "hover:scale-105"
                  }`}
                  style={{ backgroundColor: c }}
                  aria-label={`Color ${c}`}
                />
              ))}
            </div>
          </div>

          {/* Avatar URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Avatar URL
            </label>
            <input
              type="url"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://... (optional)"
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
            />
          </div>

          {/* PIN */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              PIN {isEditing && "(leave blank to keep current)"}
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="Optional 4-digit PIN"
              maxLength={6}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-3 text-base text-gray-900 dark:text-gray-100 min-h-[44px]"
            />
          </div>

          {/* Active toggle */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Active
            </span>
            <button
              type="button"
              onClick={() => setIsActive(!isActive)}
              className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors min-h-[44px] items-center ${
                isActive ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
              }`}
              role="switch"
              aria-checked={isActive}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  isActive ? "translate-x-5" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={isPending || !name.trim()}
              className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 min-h-[44px] disabled:opacity-50 transition-colors"
            >
              {isPending ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-semibold py-3 px-4 min-h-[44px] transition-colors"
            >
              Cancel
            </button>
          </div>

          {isEditing && (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={isPending}
              className="w-full rounded-xl bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 font-semibold py-3 px-4 min-h-[44px] disabled:opacity-50 transition-colors"
            >
              Delete Profile
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
