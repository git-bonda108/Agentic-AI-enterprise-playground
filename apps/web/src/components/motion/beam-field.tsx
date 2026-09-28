"use client";

type Node = { id: string; label: string; sub: string; x: number; y: number; w: number; stroke: string };

const NODES: Node[] = [
  { id: "you", label: "You", sub: "SSO sign-in", x: 20, y: 96, w: 118, stroke: "#8b5cf6" },
  { id: "pg", label: "Playground", sub: "governed gateway", x: 210, y: 96, w: 150, stroke: "#ec4899" },
  { id: "models", label: "Models", sub: "Fable to DeepSeek", x: 440, y: 18, w: 150, stroke: "#06b6d4" },
  { id: "fw", label: "Frameworks", sub: "5 SDK flavors", x: 440, y: 78, w: 150, stroke: "#06b6d4" },
  { id: "clouds", label: "Clouds", sub: "Azure, AWS, Google", x: 440, y: 138, w: 150, stroke: "#06b6d4" },
  { id: "mcp", label: "Connectors", sub: "7,500 MCP servers", x: 440, y: 198, w: 150, stroke: "#06b6d4" },
];

const PATHS: { id: string; d: string; dur: number; begin: number; color: string }[] = [
  { id: "p0", d: "M138 121 C 170 121, 180 121, 210 121", dur: 1.6, begin: 0, color: "#c4b5fd" },
  { id: "p1", d: "M360 121 C 400 121, 405 43, 440 43", dur: 2.2, begin: 0.2, color: "#a5f3fc" },
  { id: "p2", d: "M360 121 C 400 121, 405 103, 440 103", dur: 2.0, begin: 0.7, color: "#f9a8d4" },
  { id: "p3", d: "M360 121 C 400 121, 405 163, 440 163", dur: 2.4, begin: 1.1, color: "#a5f3fc" },
  { id: "p4", d: "M360 121 C 400 121, 405 223, 440 223", dur: 2.6, begin: 1.5, color: "#c4b5fd" },
];

/** Decorative beam field: traveling light dots between the user, the playground and everything it reaches. */
export function BeamField({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 610 260" className={`w-full max-w-2xl ${className}`} role="img" aria-label="The playground connects you to models, frameworks, clouds and connectors">
      <defs>
        <linearGradient id="beam-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#7c3aed" />
          <stop offset="0.5" stopColor="#ec4899" />
          <stop offset="1" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      {PATHS.map((p) => (
        <path key={p.id} id={p.id} d={p.d} fill="none" stroke="url(#beam-grad)" strokeWidth="1.2" opacity="0.5" />
      ))}
      {NODES.map((n) => (
        <g key={n.id}>
          <rect x={n.x} y={n.y} width={n.w} height={50} rx={12} fill="#12121a" stroke={n.stroke} strokeOpacity="0.55" />
          <text x={n.x + n.w / 2} y={n.y + 20} textAnchor="middle" fontSize="13" fontWeight={500} fill="#f3f4f6" fontFamily="inherit">{n.label}</text>
          <text x={n.x + n.w / 2} y={n.y + 37} textAnchor="middle" fontSize="10.5" fill="#9ca3af" fontFamily="inherit">{n.sub}</text>
        </g>
      ))}
      {PATHS.map((p) => (
        <g key={`dot-${p.id}`}>
          <circle r="6" fill={p.color} opacity="0.22">
            <animateMotion dur={`${p.dur}s`} begin={`${p.begin}s`} repeatCount="indefinite">
              <mpath href={`#${p.id}`} />
            </animateMotion>
          </circle>
          <circle r="2.8" fill={p.color}>
            <animateMotion dur={`${p.dur}s`} begin={`${p.begin}s`} repeatCount="indefinite">
              <mpath href={`#${p.id}`} />
            </animateMotion>
          </circle>
        </g>
      ))}
    </svg>
  );
}
