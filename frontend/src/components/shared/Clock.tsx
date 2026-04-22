import { useState, useEffect } from "react";
import { useHouseholdSettings } from "@/hooks/useHouseholdSettings";
import { formatTime } from "@/utils/timeFormat";

export default function Clock() {
  const [now, setNow] = useState(() => new Date());
  const { timeFormat } = useHouseholdSettings();

  useEffect(() => {
    // Sync to the start of the next minute for precise updates
    const msUntilNextMinute =
      (60 - now.getSeconds()) * 1000 - now.getMilliseconds();

    const timeout = setTimeout(() => {
      setNow(new Date());
      // After the first sync, update every 60 seconds
      const interval = setInterval(() => setNow(new Date()), 60_000);
      return () => clearInterval(interval);
    }, msUntilNextMinute);

    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Also tick every minute once synced
  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-baseline gap-4">
      <span className="text-3xl font-bold tabular-nums tracking-tight">
        {formatTime(now, "h:mm a", timeFormat)}
      </span>
      <span className="text-lg text-gray-500 dark:text-gray-400">
        {formatTime(now, "EEEE, MMMM d", timeFormat)}
      </span>
    </div>
  );
}
