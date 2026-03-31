import type { Profile } from "@/types";

interface ProfileBadgeProps {
  profile: Profile;
  size?: "sm" | "md" | "lg";
  showName?: boolean;
}

const sizeClasses = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-12 w-12 text-base",
} as const;

export default function ProfileBadge({
  profile,
  size = "md",
  showName = true,
}: ProfileBadgeProps) {
  const initial = profile.name.charAt(0).toUpperCase();

  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex shrink-0 items-center justify-center rounded-full font-bold text-white ${sizeClasses[size]}`}
        style={{ backgroundColor: profile.color }}
        aria-hidden="true"
      >
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={profile.name}
            className="h-full w-full rounded-full object-cover"
          />
        ) : (
          initial
        )}
      </div>
      {showName && (
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {profile.name}
        </span>
      )}
    </div>
  );
}
