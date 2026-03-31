import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { profiles as profilesApi } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import ProfileCard from "./ProfileCard";
import ProfileForm from "./ProfileForm";
import type { Profile } from "@/types";

export default function ProfileList() {
  const householdId = useHouseholdStore((s) => s.householdId);

  const [formState, setFormState] = useState<{
    open: boolean;
    profile?: Profile;
  }>({ open: false });

  const { data: profilesData = [], isLoading } = useQuery({
    queryKey: ["profiles", householdId],
    queryFn: () => profilesApi.getAll(householdId!).then((r) => r.data),
    enabled: !!householdId,
  });

  const activeProfiles = profilesData.filter((p) => p.is_active);
  const inactiveProfiles = profilesData.filter((p) => !p.is_active);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Profiles
        </h2>
        <button
          onClick={() => setFormState({ open: true })}
          className="rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-5 min-h-[44px] transition-colors"
        >
          + Add Profile
        </button>
      </div>

      {/* Active profiles */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {activeProfiles.map((profile) => (
          <ProfileCard
            key={profile.id}
            profile={profile}
            onClick={(p) => setFormState({ open: true, profile: p })}
          />
        ))}
      </div>

      {/* Inactive profiles */}
      {inactiveProfiles.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
            Inactive
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 opacity-60">
            {inactiveProfiles.map((profile) => (
              <ProfileCard
                key={profile.id}
                profile={profile}
                onClick={(p) => setFormState({ open: true, profile: p })}
              />
            ))}
          </div>
        </div>
      )}

      {/* Profile Form Modal */}
      {formState.open && (
        <ProfileForm
          profile={formState.profile}
          onClose={() => setFormState({ open: false })}
          onSaved={() => setFormState({ open: false })}
        />
      )}
    </div>
  );
}
