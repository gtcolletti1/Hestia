/**
 * Kid-safe palette for the pre-login splash.
 *
 * The splash is shown to anyone who walks past the wall display —
 * including small children — so we deliberately avoid neon, harsh
 * primary saturations, and strobing contrast. Colors are drawn from
 * Tailwind's "100/200/300" range to give a warm, low-energy feel.
 *
 * Exported as plain hex strings so they can be used in inline
 * ``style`` props and ``linear-gradient(...)`` strings without
 * pulling Tailwind class names through the JIT pipeline at runtime.
 */

export const KID_SAFE_PALETTE = {
  bgStart: "#FEF3C7", // amber-100
  bgEnd: "#FCE7F3", // pink-100
  bgStartDark: "#1E293B", // slate-800
  bgEndDark: "#312E81", // indigo-900

  surface: "rgba(255,255,255,0.85)",
  surfaceDark: "rgba(15,23,42,0.70)",

  text: "#1F2937",
  textMuted: "#4B5563",
  textInverse: "#F8FAFC",
  textInverseMuted: "#CBD5E1",

  morning: "#FCD34D",
  afternoon: "#7DD3FC",
  evening: "#C4B5FD",
  anytime: "#A7F3D0",

  border: "rgba(0,0,0,0.06)",
  borderDark: "rgba(255,255,255,0.10)",
} as const;

export const TIME_BLOCK_COLOR: Record<string, string> = {
  morning: KID_SAFE_PALETTE.morning,
  afternoon: KID_SAFE_PALETTE.afternoon,
  evening: KID_SAFE_PALETTE.evening,
  anytime: KID_SAFE_PALETTE.anytime,
};
