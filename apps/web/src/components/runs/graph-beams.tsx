"use client";

import type { BlueprintManifest, RunRecord } from "@/lib/playground-types";

const KIND_STROKE: Record<string, string> = { tool: "#06b6d4", llm: "#8b5cf6", gate: "#f59e0b", human: "#ec4899" };
const NODE_W = 150;
const NODE_H = 52;
const COL_GAP = 60;
const ROW_GAP = 24;

/** Lays the blueprint graph out by manifest columns and animates light dots on the edge currently being traversed. */
export function GraphBeams({ manifest, run }: { manifest: BlueprintManifest; run: RunRecord }) {
  const { nodes, edges, columns } = manifest.graph;
  const done = new Set(run.steps.map((s) => s.node));
  const lastStep = run.steps[run.steps.length - 1]?.node;
  const active = run.status === "waiting_review" ? run.steps.find((s) => s.kind === "human")?.node ?? lastStep : run.status === "running" ? nextNode(lastStep, edges, done) : null;

  const pos = new Map<string, { x: number; y: number }>();
  const maxRows = Math.max(...columns.map((c) => c.length));
  const height = maxRows * NODE_H + (maxRows - 1) * ROW_GAP + 40;
  columns.forEach((col, ci) => {
    const colHeight = col.length * NODE_H + (col.length - 1) * ROW_GAP;
    col.forEach((id, ri) => pos.set(id, { x: 20 + ci * (NODE_W + COL_GAP), y: (height - colHeight) / 2 + ri * (NODE_H + ROW_GAP) }));
  });
  const width = 40 + columns.length * NODE_W + (columns.length - 1) * COL_GAP;

  const edgePath = (a: string, b: string) => {
    const pa = pos.get(a), pb = pos.get(b);
    if (!pa || !pb) return "";
    const back = pb.x < pa.x;
    if (back) {
      const x1 = pa.x + NODE_W / 2, y1 = pa.y + NODE_H, x2 = pb.x + NODE_W / 2, y2 = pb.y + NODE_H;
      return `M${x1} ${y1} C ${x1} ${y1 + 40}, ${x2} ${y2 + 40}, ${x2} ${y2}`;
    }
    const x1 = pa.x + NODE_W, y1 = pa.y + NODE_H / 2, x2 = pb.x, y2 = pb.y + NODE_H / 2;
    return `M${x1} ${y1} C ${x1 + COL_GAP / 2} ${y1}, ${x2 - COL_GAP / 2} ${y2}, ${x2} ${y2}`;
  };

  return (
    <svg viewBox={`0 0 ${width} ${height + 20}`} className="w-full" role="img" aria-label={`${manifest.name} graph, ${run.status}`}>
      <defs>
        {/* userSpaceOnUse: a bounding-box gradient collapses to nothing on a perfectly horizontal edge */}
        <linearGradient id="gb" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={width} y2="0"><stop offset="0" stopColor="#7c3aed" /><stop offset="0.5" stopColor="#ec4899" /><stop offset="1" stopColor="#06b6d4" /></linearGradient>
      </defs>
      {edges.map(([a, b, label], i) => {
        const id = `e${i}`;
        const traversed = done.has(a) && done.has(b);
        const live = active !== null && a === lastStep && b === active;
        return (
          <g key={id}>
            <path id={id} d={edgePath(a, b)} fill="none" stroke={traversed || live ? "url(#gb)" : "var(--border-strong, #3a3a4a)"} strokeWidth={traversed || live ? 1.6 : 1} strokeDasharray={label ? "4 4" : undefined} opacity={traversed || live ? 0.9 : 0.5} />
            {label && <text fontSize="10" fill="var(--muted-foreground)" fontFamily="inherit"><textPath href={`#${id}`} startOffset="50%" textAnchor="middle">{label}</textPath></text>}
            {live && [0, 0.6, 1.2].map((delay) => (
              <g key={delay}>
                <circle r="6" fill="#a78bfa" opacity="0.25"><animateMotion dur="1.8s" begin={`${delay}s`} repeatCount="indefinite"><mpath href={`#${id}`} /></animateMotion></circle>
                <circle r="2.8" fill="#e9d5ff"><animateMotion dur="1.8s" begin={`${delay}s`} repeatCount="indefinite"><mpath href={`#${id}`} /></animateMotion></circle>
              </g>
            ))}
          </g>
        );
      })}
      {nodes.map((n) => {
        const p = pos.get(n.id);
        if (!p) return null;
        const isDone = done.has(n.id);
        const isActive = n.id === active;
        const isWaiting = run.status === "waiting_review" && n.kind === "human" && !run.steps.some((s) => s.node === n.id && s.kind === "human" && s.summary.startsWith("Human"));
        const stroke = KIND_STROKE[n.kind] ?? "#8b5cf6";
        return (
          <g key={n.id} transform={`translate(${p.x},${p.y})`}>
            {(isActive || isWaiting) && <rect x={-4} y={-4} width={NODE_W + 8} height={NODE_H + 8} rx={14} fill="none" stroke={stroke} strokeOpacity="0.5" className="animate-pulse-glow" />}
            <rect width={NODE_W} height={NODE_H} rx={12} fill="var(--card)" stroke={stroke} strokeOpacity={isDone || isActive || isWaiting ? 0.9 : 0.35} strokeWidth={1.2} />
            <circle cx={14} cy={NODE_H / 2} r={4} fill={isDone ? "#10b981" : isActive || isWaiting ? stroke : "var(--muted-foreground)"} opacity={isDone || isActive || isWaiting ? 1 : 0.4} />
            <text x={26} y={NODE_H / 2 - 6} fontSize="12" fontWeight={500} fill="var(--foreground)" fontFamily="inherit">{n.label}</text>
            <text x={26} y={NODE_H / 2 + 10} fontSize="10" fill="var(--muted-foreground)" fontFamily="inherit">{n.kind === "llm" ? "model" : n.kind === "human" ? "human review" : n.kind === "gate" ? "deterministic gate" : "tool"}</text>
          </g>
        );
      })}
    </svg>
  );
}

function nextNode(last: string | undefined, edges: [string, string, string?][], done: Set<string>): string | null {
  if (!last) return edges[0]?.[0] ?? null;
  const candidates = edges.filter(([a]) => a === last).map(([, b]) => b);
  return candidates.find((c) => !done.has(c)) ?? candidates[0] ?? null;
}
