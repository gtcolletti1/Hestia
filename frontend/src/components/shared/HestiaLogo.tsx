interface HestiaLogoProps {
  size?: number;
  className?: string;
  /** Show the "Hestia" wordmark next to the icon. */
  withWordmark?: boolean;
}

/**
 * Hestia brand mark: an asymmetric flame rising from a Greek tripod brazier.
 *
 * Inspired by classical depictions of the eternal hearth fire — an
 * asymmetric "wind-blown" flame (rather than a symmetric teardrop) on
 * top of a three-legged bronze brazier. Two warm gradients give the
 * flame depth without looking cartoonish; the brazier inherits
 * `currentColor` so it adapts to light/dark themes.
 *
 * Gradient ids are randomised per-instance so multiple logos on the
 * same page don't collide.
 */
export default function HestiaLogo({
  size = 32,
  className = "",
  withWordmark = false,
}: HestiaLogoProps) {
  const uid = Math.random().toString(36).slice(2, 9);
  const flameId = `hestia-flame-${uid}`;
  const coreId = `hestia-core-${uid}`;
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
          {/* Outer flame: deep terracotta base → orange middle → gold tip */}
          <linearGradient id={flameId} x1="0.5" y1="1" x2="0.5" y2="0">
            <stop offset="0%" stopColor="#7c2d12" />
            <stop offset="35%" stopColor="#c2410c" />
            <stop offset="75%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#fde68a" />
          </linearGradient>
          {/* Inner core: brighter, sits inside outer */}
          <linearGradient id={coreId} x1="0.5" y1="1" x2="0.5" y2="0">
            <stop offset="0%" stopColor="#ea580c" />
            <stop offset="60%" stopColor="#fcd34d" />
            <stop offset="100%" stopColor="#fffbeb" />
          </linearGradient>
        </defs>

        {/* Tripod legs */}
        <path
          d="M9 24 L7 30 M16 25 L16 30 M23 24 L25 30"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          opacity="0.85"
        />
        {/* Brazier bowl (shallow cup) */}
        <path
          d="M6 22 Q16 27 26 22 L24 24.5 Q16 28 8 24.5 Z"
          fill="currentColor"
          opacity="0.85"
        />
        {/* Bowl rim highlight */}
        <path
          d="M7 22 Q16 25.5 25 22"
          stroke="currentColor"
          strokeWidth="0.8"
          opacity="0.4"
          fill="none"
        />

        {/* Outer flame — asymmetric, leans/curls slightly to the left at the
            tip, like a wind-touched torch flame. */}
        <path
          d="M10 22
             C 7 18, 8 14, 11 12
             C 9 8, 12 4, 15 3
             C 14 6, 17 6, 18 5
             C 21 9, 22 14, 20 18
             C 22 20, 21 22, 19 22
             Z"
          fill={`url(#${flameId})`}
        />
        {/* Inner core flame — narrower, sits within outer */}
        <path
          d="M14 21
             C 12 18, 13 14, 15 12
             C 14 10, 15 8, 16 7
             C 18 10, 19 14, 18 17
             C 19 19, 18 21, 16 21
             Z"
          fill={`url(#${coreId})`}
          opacity="0.95"
        />
        {/* Bright wisp at the tip */}
        <path
          d="M15.5 7 C 16.2 9, 16.5 11, 16 13"
          stroke="#fffbeb"
          strokeWidth="0.7"
          strokeLinecap="round"
          opacity="0.75"
          fill="none"
        />
      </svg>
      {withWordmark && (
        <span className="font-semibold tracking-tight">Hestia</span>
      )}
    </span>
  );
}

