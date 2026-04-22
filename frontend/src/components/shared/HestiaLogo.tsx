interface HestiaLogoProps {
  size?: number;
  className?: string;
  /** Show the "Hestia" wordmark next to the icon. */
  withWordmark?: boolean;
}

/**
 * Hestia brand mark: a stylized hearth flame.
 *
 * Uses an in-SVG gradient (amber → orange → red) for the flame and
 * `currentColor` for the hearth ledge, so the ledge inherits the
 * surrounding text color and adapts to light/dark themes.
 *
 * The gradient id is randomised per-instance so multiple logos on the
 * same page don't collide.
 */
export default function HestiaLogo({
  size = 32,
  className = "",
  withWordmark = false,
}: HestiaLogoProps) {
  const gradId = `hestia-flame-${Math.random().toString(36).slice(2, 9)}`;
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fde68a" />
            <stop offset="45%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#b91c1c" />
          </linearGradient>
        </defs>
        {/* hearth ledge — adapts to text color */}
        <path
          d="M5 28 H27"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          opacity="0.55"
        />
        {/* outer flame */}
        <path
          d="M16 3.5 C 21 9, 24 13.5, 23 18.5 C 22 23.5, 19 26.5, 16 27.5 C 13 26.5, 10 23.5, 9 18.5 C 8 13.5, 11 9, 16 3.5 Z"
          fill={`url(#${gradId})`}
        />
        {/* inner highlight */}
        <path
          d="M16 11 C 18 14, 18.5 17, 17.5 20 C 17 22, 15 22, 14.5 20 C 13.5 17, 14 14, 16 11 Z"
          fill="#fef3c7"
          opacity="0.85"
        />
      </svg>
      {withWordmark && (
        <span className="font-semibold tracking-tight">Hestia</span>
      )}
    </span>
  );
}
