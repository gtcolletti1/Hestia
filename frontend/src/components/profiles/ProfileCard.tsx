import type { Profile } from "@/types";

const ROLE_STYLES: Record<
  Profile["role"],
  { bg: string; text: string; label: string }
> = {
  admin: {
    bg: "bg-purple-100 dark:bg-purple-900/40",
    text: "text-purple-700 dark:text-purple-300",
    label: "Admin",
  },
  standard: {
    bg: "bg-blue-100 dark:bg-blue-900/40",
    text: "text-blue-700 dark:text-blue-300",
    label: "Standard",
  },
  kid: {
    bg: "bg-green-100 dark:bg-green-900/40",
    text: "text-green-700 dark:text-green-300",
    label: "Kid",
  },
};

interface ProfileCardProps {
  profile: Profile;
  onClick?: (profile: Profile) => void;
}

export default function ProfileCard({ profile, onClick }: ProfileCardProps) {
  const role = ROLE_STYLES[profile.role];

  return (
    <button
      type="button"
      onClick={() => onClick?.(profile)}
      className="w-full rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow text-center min-h-[44px] relative overflow-hidden"
    >
      {/* Color strip */}
      <div
        className="absolute top-0 left-0 right-0 h-1.5"
        style={{ backgroundColor: profile.color }}
      />

      {/* Avatar */}
      <div className="flex justify-center mb-3 mt-1">
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={profile.name}
            className="h-16 w-16 rounded-full object-cover border-2"
            style={{ borderColor: profile.color }}
          />
        ) : (
          <div
            className="h-16 w-16 rounded-full flex items-center justify-center text-2xl font-bold text-white"
            style={{ backgroundColor: profile.color }}
          >
            {profile.name.charAt(0).toUpperCase()}
          </div>
        )}
      </div>

      {/* Name */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        {profile.name}
      </h3>

      {/* Role badge */}
      <span
        className={`inline-block mt-1.5 rounded-full px-3 py-0.5 text-xs font-medium ${role.bg} ${role.text}`}
      >
        {role.label}
      </span>

      {/* Inactive indicator */}
      {!profile.is_active && (
        <div className="mt-2 text-xs text-gray-400 dark:text-gray-500 italic">
          Inactive
        </div>
      )}
    </button>
  );
}
