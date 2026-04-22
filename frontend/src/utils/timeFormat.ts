import { format as fnsFormat } from "date-fns";

type TimeFormat = "12h" | "24h";

const FORMAT_MAP: Record<string, Record<TimeFormat, string>> = {
  "h:mm a":              { "12h": "h:mm a",              "24h": "HH:mm" },
  "h:mm":                { "12h": "h:mm",                "24h": "HH:mm" },
  "h a":                 { "12h": "h a",                 "24h": "HH:mm" },
  "EEE, MMM d · h:mm a": { "12h": "EEE, MMM d · h:mm a", "24h": "EEE, MMM d · HH:mm" },
};

/**
 * Format a date using the household's 12h/24h preference.
 * Pass the 12-hour pattern as `pattern` — it auto-converts for 24h mode.
 */
export function formatTime(
  date: Date | number,
  pattern: string,
  timeFormat: TimeFormat = "12h",
): string {
  const resolved = FORMAT_MAP[pattern]?.[timeFormat] ?? pattern;
  return fnsFormat(date, resolved);
}
