import { cn } from "@/lib/utils";

/**
 * The brand mark: an agent graph. A bright core node with three satellite agents on an orbit, joined by beams,
 * and a spark at the top right for the playground's experimental side. Drawn as a single SVG so it scales from
 * the favicon to the sign-in page, on the brand gradient tile.
 */
export function BrandMark({ size = 32, className, tile = true }: { size?: number; className?: string; tile?: boolean }) {
  return (
    <span
      className={cn("relative inline-grid shrink-0 place-items-center rounded-[26%] text-white", tile && "gradient-brand animate-gradient-shift shadow-md shadow-violet-900/30", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg viewBox="0 0 64 64" width={size * 0.78} height={size * 0.78} fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="bm-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.75" />
          </radialGradient>
        </defs>
        <circle cx="32" cy="32" r="21" stroke="#ffffff" strokeOpacity="0.45" strokeWidth="1.6" strokeDasharray="3.5 4.5" />
        <path d="M32 32 L32 11" stroke="#ffffff" strokeOpacity="0.85" strokeWidth="2.4" strokeLinecap="round" />
        <path d="M32 32 L13.8 42.5" stroke="#ffffff" strokeOpacity="0.85" strokeWidth="2.4" strokeLinecap="round" />
        <path d="M32 32 L50.2 42.5" stroke="#ffffff" strokeOpacity="0.85" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="32" cy="11" r="5" fill="#ffffff" />
        <circle cx="13.8" cy="42.5" r="5" fill="#ffffff" />
        <circle cx="50.2" cy="42.5" r="5" fill="#ffffff" />
        <circle cx="32" cy="32" r="8.5" fill="url(#bm-core)" />
        <circle cx="32" cy="32" r="8.5" stroke="#ffffff" strokeOpacity="0.9" strokeWidth="1.5" />
        <path d="M53 8 L54.6 12.4 L59 14 L54.6 15.6 L53 20 L51.4 15.6 L47 14 L51.4 12.4 Z" fill="#ffffff" />
      </svg>
    </span>
  );
}
