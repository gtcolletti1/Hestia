import { useQuery } from "@tanstack/react-query";
import { weather } from "@/api/endpoints";
import { useHouseholdStore } from "@/stores/householdStore";

interface WeatherData {
  temp: number | null;
  feels_like: number | null;
  description: string | null;
  icon: string | null;
  humidity: number | null;
  wind_speed: number | null;
  units: string;
  forecast: Array<{
    date: string;
    high: number;
    low: number;
    description: string;
    icon: string;
  }>;
}

const ICON_MAP: Record<string, string> = {
  "01d": "☀️",
  "01n": "🌙",
  "02d": "⛅",
  "02n": "☁️",
  "03d": "☁️",
  "03n": "☁️",
  "04d": "☁️",
  "04n": "☁️",
  "09d": "🌧️",
  "09n": "🌧️",
  "10d": "🌦️",
  "10n": "🌧️",
  "11d": "⛈️",
  "11n": "⛈️",
  "13d": "🌨️",
  "13n": "🌨️",
  "50d": "🌫️",
  "50n": "🌫️",
};

function toF(celsius: number): number {
  return Math.round(celsius * 9 / 5 + 32);
}

function formatTemp(celsius: number | null, units: string): string {
  if (celsius === null) return "--";
  if (units === "imperial") return `${toF(celsius)}°`;
  return `${Math.round(celsius)}°`;
}

function getDayLabel(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  const today = new Date();
  const tomorrow = new Date();
  tomorrow.setDate(today.getDate() + 1);

  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === tomorrow.toDateString()) return "Tomorrow";
  return d.toLocaleDateString("en-US", { weekday: "short" });
}

export default function WeatherWidget() {
  const householdId = useHouseholdStore((s) => s.householdId);

  const { data, isLoading, isError } = useQuery<WeatherData>({
    queryKey: ["weather", householdId],
    queryFn: async () => {
      const res = await weather.get(householdId!);
      return res.data;
    },
    enabled: !!householdId,
    refetchInterval: 15 * 60 * 1000, // 15 minutes
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-20 rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-8 w-24 rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-3 w-32 rounded bg-gray-200 dark:bg-gray-700" />
        </div>
      </div>
    );
  }

  // Don't render if weather isn't configured or errored
  if (isError || !data || data.temp === null) {
    return null;
  }

  const units = data.units || "imperial";
  const emoji = ICON_MAP[data.icon ?? ""] ?? "🌤️";

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
        Weather
      </h3>

      {/* Current conditions */}
      <div className="flex items-center gap-3">
        <span className="text-4xl" role="img" aria-label={data.description ?? "weather"}>
          {emoji}
        </span>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {formatTemp(data.temp, units)}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
            {data.description}
          </p>
        </div>
      </div>

      {/* Details */}
      <div className="flex gap-4 text-xs text-gray-400 dark:text-gray-500">
        <span>Feels {formatTemp(data.feels_like, units)}</span>
        {data.humidity !== null && <span>💧 {data.humidity}%</span>}
        {data.wind_speed !== null && (
          <span>💨 {units === "imperial" ? `${Math.round(data.wind_speed * 2.237)} mph` : `${Math.round(data.wind_speed)} m/s`}</span>
        )}
      </div>

      {/* 3-day forecast */}
      {data.forecast.length > 0 && (
        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
          {data.forecast.map((day) => (
            <div key={day.date} className="text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                {getDayLabel(day.date)}
              </p>
              <p className="text-lg">
                {ICON_MAP[day.icon ?? ""] ?? "🌤️"}
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-300">
                <span className="font-semibold">{formatTemp(day.high, units)}</span>
                {" "}
                <span className="text-gray-400">{formatTemp(day.low, units)}</span>
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
