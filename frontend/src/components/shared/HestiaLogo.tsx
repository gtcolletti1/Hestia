interface HestiaLogoProps {
  size?: number;
  className?: string;
  /** Show the "Hestia" wordmark next to the icon. */
  withWordmark?: boolean;
}

/**
 * Hestia brand mark: an asymmetric multi-tongue flame above a small
 * Greek tripod brazier.
 *
 * Design notes for a more "real fire" feel at icon size:
 *  - No outline strokes on the flame shapes; silhouettes alone read as
 *    cartoonish.
 *  - Each flame tongue uses a vertical gradient that fades to alpha 0
 *    at the tip, so the edges dissolve like real fire instead of
 *    ending in a hard contour.
 *  - A soft Gaussian blur is applied only to the flame group, giving
 *    it that "luminous" quality without smudging the brazier.
 *  - A bright white-hot core at the base + warm radial halo behind
 *    everything provide depth and ambient glow.
 *  - The brazier (currentColor) is small and stays crisp so the mark
 *    still has a recognisable anchor.
 *
 * Larger 64x64 viewBox gives finer path control than a 32x32 grid.
 * Gradient ids are randomised per-instance to avoid collisions.
 */
export default function HestiaLogo({
  size = 32,
  className = "",
  withWordmark = false,
}: HestiaLogoProps) {
  const uid = Math.random().toString(36).slice(2, 9);
  const halo = `hestia-halo-${uid}`;
  const tA = `hestia-tongueA-${uid}`;
  const tB = `hestia-tongueB-${uid}`;
  const hot = `hestia-hot-${uid}`;
  const soft = `hestia-soft-${uid}`;
  const ember = `hestia-ember-${uid}`;
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          {/* Warm ambient halo behind the flame — deeper bronze tones */}
          <radialGradient id={halo} cx="50%" cy="60%" r="55%">
            <stop offset="0%" stopColor="#d97706" stopOpacity="0.55" />
            <stop offset="55%" stopColor="#b45309" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#451a03" stopOpacity="0" />
          </radialGradient>
          {/* Central tongue: hot copper base, fades at tip */}
          <linearGradient id={tA} x1="0.5" y1="1" x2="0.5" y2="0">
            <stop offset="0%" stopColor="#fef3c7" stopOpacity="0.95" />
            <stop offset="22%" stopColor="#fbbf24" stopOpacity="0.92" />
            <stop offset="55%" stopColor="#c2410c" stopOpacity="0.9" />
            <stop offset="82%" stopColor="#7f1d1d" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#451a03" stopOpacity="0" />
          </linearGradient>
          {/* Outer / wisp tongues: dimmer bronze-red, also fades */}
          <linearGradient id={tB} x1="0.5" y1="1" x2="0.5" y2="0">
            <stop offset="0%" stopColor="#d97706" stopOpacity="0.78" />
            <stop offset="55%" stopColor="#b91c1c" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#7f1d1d" stopOpacity="0" />
          </linearGradient>
          {/* White-hot combustion core */}
          <radialGradient id={hot} cx="50%" cy="70%" r="50%">
            <stop offset="0%" stopColor="#fffbeb" stopOpacity="1" />
            <stop offset="45%" stopColor="#fde68a" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#d97706" stopOpacity="0" />
          </radialGradient>
          {/* Soft blur for the flame group only */}
          <filter id={soft} x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="0.7" />
          </filter>
          {/* Tiny glow filter for floating embers */}
          <filter id={ember} x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="0.45" />
          </filter>
        </defs>

        {/* Tripod brazier — drawn first, behind the halo + flame */}
        <g opacity="0.9">
          <path
            d="M18 48 L12 60 M32 50 L32 60 M46 48 L52 60"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
          <path
            d="M10 44 Q32 54 54 44 L50 48 Q32 56 14 48 Z"
            fill="currentColor"
          />
          <path
            d="M12 44 Q32 50 52 44"
            stroke="currentColor"
            strokeWidth="1"
            opacity="0.45"
            fill="none"
          />
        </g>

        {/* Ambient warm halo */}
        <ellipse cx="32" cy="32" rx="22" ry="26" fill={`url(#${halo})`} />

        {/* Flame group — softly blurred for luminous feel */}
        <g filter={`url(#${soft})`}>
          {/* Wide outer flame body */}
          <path
            d="M16 44
               C 10 34, 14 22, 22 14
               C 26 8, 32 4, 36 8
               C 44 16, 46 28, 44 36
               C 48 42, 44 44, 38 44 Z"
            fill={`url(#${tB})`}
          />
          {/* Tall asymmetric central tongue */}
          <path
            d="M24 44
               C 20 34, 26 24, 28 16
               C 29 10, 29 6, 30 4
               C 32 8, 34 14, 36 22
               C 38 30, 38 38, 36 44 Z"
            fill={`url(#${tA})`}
          />
          {/* Left wisp */}
          <path
            d="M14 44
               C 12 38, 12 28, 16 22
               C 18 18, 20 18, 20 22
               C 22 28, 22 36, 22 44 Z"
            fill={`url(#${tB})`}
          />
          {/* Right wisp */}
          <path
            d="M40 44
               C 42 38, 44 30, 46 24
               C 47 22, 48 22, 48 26
               C 48 34, 46 40, 44 44 Z"
            fill={`url(#${tB})`}
          />
        </g>

        {/* White-hot core, sharp (no blur) */}
        <ellipse cx="32" cy="38" rx="5" ry="7" fill={`url(#${hot})`} />

        {/* Floating embers — drifting up & away from the flame tip.
            Asymmetric placement, varied sizes, with their own soft glow. */}
        <g filter={`url(#${ember})`}>
          <circle cx="22" cy="6" r="1.1" fill="#fbbf24" opacity="0.95" />
          <circle cx="38" cy="10" r="0.9" fill="#fde68a" opacity="0.9" />
          <circle cx="44" cy="3" r="0.7" fill="#f59e0b" opacity="0.85" />
        </g>
      </svg>
      {withWordmark && (
        <span className="font-semibold tracking-tight">Hestia</span>
      )}
    </span>
  );
}


