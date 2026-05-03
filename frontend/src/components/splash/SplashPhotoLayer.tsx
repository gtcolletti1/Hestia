import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { photos } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";
import { formatTime } from "@/utils/timeFormat";

interface Photo {
  id: string;
  url: string;
  caption: string | null;
}

interface SplashPhotoLayerProps {
  /** Seconds between photo transitions (defaults to 10). */
  transitionSeconds?: number;
  /** Inherits the household's clock format. */
  timeFormat: "12h" | "24h";
}

/**
 * The "photo" content layer for the splash. Visually identical to the
 * authenticated screensaver: a single fullbleed photo with crossfade,
 * a corner clock, and an optional caption.
 *
 * NOTE: this component fetches via ``/api/photos``, which is currently
 * an authenticated endpoint. Pre-login it returns 401 and the photo
 * list stays empty — the splash falls back to the static
 * ``/hestia-splash.png`` background. A future PR can add an
 * unauthenticated splash-photos endpoint if households want to show
 * actual family photos before sign-in. For now the fallback is
 * deliberately privacy-safe.
 */
export default function SplashPhotoLayer({
  transitionSeconds = 10,
  timeFormat,
}: SplashPhotoLayerProps) {
  const householdId = useHouseholdStore((s) => s.householdId);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [now, setNow] = useState(new Date());

  const { data: photoList = [] } = useQuery<Photo[]>({
    queryKey: ["splash-photos", householdId],
    queryFn: async () => {
      try {
        const res = await photos.getAll(householdId!);
        return res.data;
      } catch {
        return [];
      }
    },
    enabled: !!householdId,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (photoList.length <= 1) return;
    const id = window.setInterval(() => {
      setCurrentIndex((i) => (i + 1) % photoList.length);
    }, transitionSeconds * 1000);
    return () => window.clearInterval(id);
  }, [photoList.length, transitionSeconds]);

  const current = photoList[currentIndex];

  return (
    <div className="absolute inset-0 flex h-full w-full items-center justify-center">
      {/* When the household has uploaded photos, paint the current one
          over the global hearth backdrop. With no photos (or pre-login
          401), we let the hearth show through and just render the
          clock overlay. */}
      {current && (
        <img
          key={current.id}
          src={current.url}
          alt={current.caption ?? ""}
          className="absolute inset-0 h-full w-full object-cover opacity-90 transition-opacity duration-1000"
          draggable={false}
        />
      )}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />
      <div className="relative z-10 text-center text-white drop-shadow-lg">
        <p className="text-[clamp(4rem,14vw,10rem)] font-thin tabular-nums">
          {formatTime(now, "h:mm", timeFormat)}
        </p>
        <p className="mt-2 text-[clamp(1.25rem,2.5vw,2rem)] font-light opacity-90">
          {format(now, "EEEE, MMMM d")}
        </p>
        {current?.caption && (
          <p className="mt-6 text-lg font-light italic opacity-70">{current.caption}</p>
        )}
      </div>
    </div>
  );
}
