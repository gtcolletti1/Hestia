import { useState, useEffect } from "react";
import { format } from "date-fns";

export default function Clock() {
  const [now, setNow] = useState(() => new Date());

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
        {format(now, "h:mm a")}
      </span>
      <span className="text-lg text-gray-500 dark:text-gray-400">
        {format(now, "EEEE, MMMM d")}
      </span>
    </div>
  );
}
