import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { formatTime } from "@/utils/timeFormat";
import { photos } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";

interface Photo {
  id: string;
  url: string;
  caption: string | null;
}

interface ScreensaverOverlayProps {
  onDismiss: () => void;
  transitionSeconds?: number;
}

export default function ScreensaverOverlay({ onDismiss, transitionSeconds = 10 }: ScreensaverOverlayProps) {
  const householdId = useHouseholdStore((s) => s.householdId);
  const { timeFormat } = useHouseholdSettings();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [now, setNow] = useState(new Date());

  const { data: photoList = [] } = useQuery<Photo[]>({
    queryKey: ["photos", householdId],
    queryFn: async () => {
      const res = await photos.getAll(householdId!);
      return res.data;
    },
    enabled: !!householdId,
    staleTime: 5 * 60 * 1000,
  });

  // Update clock every minute
  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(interval);
  }, []);

  // Rotate photos based on configured transition speed
  useEffect(() => {
    if (photoList.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % photoList.length);
    }, transitionSeconds * 1000);
    return () => clearInterval(interval);
  }, [photoList.length, transitionSeconds]);

  const handleDismiss = useCallback(
    (e: React.MouseEvent | React.TouchEvent | React.KeyboardEvent) => {
      e.stopPropagation();
      onDismiss();
    },
    [onDismiss],
  );

  const currentPhoto = photoList[currentIndex];

  return (
    <div
      className="fixed inset-0 z-[100] bg-black flex items-center justify-center cursor-none"
      onClick={handleDismiss}
      onTouchStart={handleDismiss}
      onKeyDown={handleDismiss}
      tabIndex={0}
      role="button"
      aria-label="Dismiss screensaver"
    >
      {/* Background photo with crossfade */}
      {currentPhoto && (
        <img
          key={currentPhoto.id}
          src={currentPhoto.url}
          alt={currentPhoto.caption ?? "Family photo"}
          className="absolute inset-0 w-full h-full object-cover animate-fade-in opacity-60"
          draggable={false}
        />
      )}

      {/* Gradient overlay for readability */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />

      {/* Clock and date */}
      <div className="relative z-10 text-center text-white select-none">
        <p className="text-8xl font-thin tracking-wider tabular-nums">
          {formatTime(now, "h:mm", timeFormat)}
        </p>
        <p className="text-3xl font-light mt-2 tracking-wide opacity-90">
          {format(now, "EEEE, MMMM d")}
        </p>

        {currentPhoto?.caption && (
          <p className="text-lg font-light mt-6 opacity-70 italic">
            {currentPhoto.caption}
          </p>
        )}
      </div>

      {/* No photos hint */}
      {photoList.length === 0 && (
        <div className="absolute bottom-8 text-white/40 text-sm">
          Add photos in Settings to display here
        </div>
      )}

      {/* Photo counter */}
      {photoList.length > 1 && (
        <div className="absolute bottom-4 right-4 text-white/30 text-xs">
          {currentIndex + 1} / {photoList.length}
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 0.6; }
        }
        .animate-fade-in {
          animation: fadeIn 2s ease-in-out;
        }
      `}</style>
    </div>
  );
}
