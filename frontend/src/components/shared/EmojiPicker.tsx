import { useEffect, useRef, useState } from "react";

interface EmojiPickerProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  ariaLabel?: string;
}

// Curated emoji set tuned for family-hub routines / chores / lists.
// Grouped to make scanning fast on a wall-mounted touchscreen.
const EMOJI_GROUPS: { name: string; emojis: string[] }[] = [
  {
    name: "Hygiene",
    emojis: ["🪥", "🦷", "🧼", "🧴", "🛁", "🚿", "🧻", "💧", "✂️", "💇", "🧽", "🪞"],
  },
  {
    name: "Bedtime",
    emojis: ["🛏️", "😴", "🌙", "⭐", "📖", "🧸", "🌜", "🦉", "🕯️", "💤"],
  },
  {
    name: "Food & Drink",
    emojis: ["🍳", "🥣", "🥪", "🍎", "🥕", "🥛", "💧", "🍌", "🍞", "🧃", "🍽️", "☕", "🍪", "🥗"],
  },
  {
    name: "School & Learn",
    emojis: ["🎒", "📚", "✏️", "📝", "🖍️", "🧮", "🎨", "🔬", "🧠", "🏫", "📐", "🖥️"],
  },
  {
    name: "Chores",
    emojis: ["🧺", "🧹", "🧽", "🗑️", "♻️", "🪣", "🧴", "🧼", "🪟", "🛏️", "👕", "🍽️", "🪴"],
  },
  {
    name: "Activity",
    emojis: ["🏃", "🚴", "⚽", "🏀", "🎮", "🎵", "🎹", "🎸", "🧩", "🎲", "🚶", "🧘", "🏊"],
  },
  {
    name: "Time & Weather",
    emojis: ["⏰", "⌛", "🌅", "☀️", "🌤️", "⛅", "🌧️", "❄️", "🌇", "🌙", "🕐"],
  },
  {
    name: "Pets & Outdoors",
    emojis: ["🐶", "🐱", "🐰", "🐦", "🦴", "🌳", "🌻", "🌼", "🪴", "🚗", "🚌"],
  },
  {
    name: "Mood & Reward",
    emojis: ["⭐", "🌟", "✨", "🏆", "🎉", "👍", "❤️", "🥰", "😊", "🙌", "🎁"],
  },
];

export default function EmojiPicker({
  value,
  onChange,
  placeholder = "🙂",
  ariaLabel = "Choose an icon",
}: EmojiPickerProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleDocClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleDocClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleDocClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const select = (emoji: string) => {
    onChange(emoji);
    setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={ariaLabel}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="touch-target flex h-11 w-14 items-center justify-center rounded-lg border border-gray-300 bg-white text-xl hover:border-blue-400 hover:bg-blue-50 dark:border-gray-600 dark:bg-gray-800 dark:hover:border-blue-500 dark:hover:bg-gray-700"
      >
        <span aria-hidden="true">
          {value || <span className="text-gray-400">{placeholder}</span>}
        </span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Emoji picker"
          className="absolute left-0 top-full z-50 mt-2 w-80 max-h-96 overflow-y-auto rounded-xl border border-gray-200 bg-white p-3 shadow-xl dark:border-gray-700 dark:bg-gray-800"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Pick an icon
            </span>
            {value && (
              <button
                type="button"
                onClick={() => select("")}
                className="rounded-md px-2 py-1 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30"
              >
                Clear
              </button>
            )}
          </div>
          {EMOJI_GROUPS.map((group) => (
            <div key={group.name} className="mb-3 last:mb-0">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                {group.name}
              </div>
              <div className="grid grid-cols-8 gap-1">
                {group.emojis.map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => select(emoji)}
                    className={`flex h-9 w-9 items-center justify-center rounded-md text-xl transition-colors hover:bg-blue-100 dark:hover:bg-blue-900/40 ${
                      value === emoji
                        ? "bg-blue-100 ring-2 ring-blue-500 dark:bg-blue-900/40"
                        : ""
                    }`}
                    aria-label={`Select ${emoji}`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
