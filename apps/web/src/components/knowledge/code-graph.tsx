"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphEdge, GraphNode } from "@/lib/playground-types";

const PALETTE = ["#8b5cf6", "#ec4899", "#06b6d4", "#10b981", "#f59e0b", "#e11d48", "#3b82f6", "#a3e635", "#f97316", "#14b8a6"];
const KIND_RADIUS: Record<string, number> = { folder: 7, file: 6, class: 5, component: 5, function: 4, method: 3, section: 4 };

type Sim = { x: number; y: number; vx: number; vy: number };

/** A small force-directed layout in plain SVG: repulsion between nodes, springs on edges, gravity to the centre. */
export function CodeGraph({ nodes, edges, width = 960, height = 560 }: { nodes: GraphNode[]; edges: GraphEdge[]; width?: number; height?: number }) {
  const [positions, setPositions] = useState<Record<string, Sim>>({});
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const frame = useRef<number | null>(null);

  const index = useMemo(() => new Map(nodes.map((n, i) => [n.id, i])), [nodes]);
  const neighbours = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const e of edges) {
      if (!m.has(e.source)) m.set(e.source, new Set());
      if (!m.has(e.target)) m.set(e.target, new Set());
      m.get(e.source)!.add(e.target);
      m.get(e.target)!.add(e.source);
    }
    return m;
  }, [edges]);

  useEffect(() => {
    if (nodes.length === 0) return;
    // Fruchterman-Reingold: repulsion k²/d, attraction d²/k along edges, a cooling temperature that caps movement per tick.
    const n = nodes.length;
    const k = Math.sqrt((width * height) / n) * 0.75;
    const sims: Sim[] = nodes.map((node, i) => {
      const angle = (i / n) * Math.PI * 2 + node.community * 0.7;
      const r = Math.min(width, height) * (0.18 + 0.22 * ((node.community * 37) % 10) / 10);
      return { x: width / 2 + Math.cos(angle) * r, y: height / 2 + Math.sin(angle) * r, vx: 0, vy: 0 };
    });
    const edgeIdx = edges.map((e) => [index.get(e.source), index.get(e.target)] as const).filter(([a, b]) => a !== undefined && b !== undefined) as [number, number][];
    let tick = 0;
    let temperature = width / 8;
    const step = () => {
      for (const s of sims) { s.vx = 0; s.vy = 0; }
      for (let i = 0; i < n; i += 1) {
        for (let j = i + 1; j < n; j += 1) {
          let dx = sims[j].x - sims[i].x, dy = sims[j].y - sims[i].y;
          let d = Math.sqrt(dx * dx + dy * dy);
          if (d < 0.5) { dx = (i % 3) - 1 || 0.5; dy = (j % 3) - 1 || -0.5; d = Math.sqrt(dx * dx + dy * dy); }
          const f = (k * k) / d / d;
          const fx = dx * f, fy = dy * f;
          sims[i].vx -= fx; sims[i].vy -= fy; sims[j].vx += fx; sims[j].vy += fy;
        }
      }
      for (const [a, b] of edgeIdx) {
        const dx = sims[b].x - sims[a].x, dy = sims[b].y - sims[a].y;
        const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
        const f = d / k;
        const fx = dx * f, fy = dy * f;
        sims[a].vx += fx; sims[a].vy += fy; sims[b].vx -= fx; sims[b].vy -= fy;
      }
      for (const s of sims) {
        s.vx += (width / 2 - s.x) * 0.05; s.vy += (height / 2 - s.y) * 0.05;
        const len = Math.sqrt(s.vx * s.vx + s.vy * s.vy) || 1;
        const move = Math.min(len, temperature);
        s.x = Math.max(14, Math.min(width - 14, s.x + (s.vx / len) * move));
        s.y = Math.max(14, Math.min(height - 14, s.y + (s.vy / len) * move));
      }
      temperature = Math.max(0.5, temperature * 0.93);
      tick += 1;
      if (tick % 2 === 0 || tick >= 140) setPositions(Object.fromEntries(nodes.map((node, i) => [node.id, { ...sims[i] }])));
      if (tick < 140) frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
    return () => { if (frame.current) cancelAnimationFrame(frame.current); };
  }, [nodes, edges, index, width, height]);

  const focus = hover ?? selected?.id ?? null;
  const focusSet = focus ? new Set([focus, ...(neighbours.get(focus) ?? [])]) : null;

  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_260px]">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[560px] w-full rounded-2xl border bg-[#0a0a14]" role="img" aria-label={`Code graph with ${nodes.length} nodes and ${edges.length} edges`} data-testid="code-graph">
        <defs>
          <radialGradient id="graph-glow"><stop offset="0%" stopColor="#7c3aed" stopOpacity="0.35" /><stop offset="100%" stopColor="#7c3aed" stopOpacity="0" /></radialGradient>
        </defs>
        <rect width={width} height={height} fill="url(#graph-glow)" opacity="0.5" />
        {edges.map((e, i) => {
          const a = positions[e.source], b = positions[e.target];
          if (!a || !b) return null;
          const dim = focusSet && !(focusSet.has(e.source) && focusSet.has(e.target));
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={e.kind === "imports" ? "#06b6d4" : e.kind === "calls" ? "#ec4899" : "#475569"} strokeOpacity={dim ? 0.06 : e.kind === "contains" ? 0.25 : 0.55} strokeWidth={dim ? 0.6 : 1} />;
        })}
        {nodes.map((n) => {
          const p = positions[n.id];
          if (!p) return null;
          const dim = focusSet && !focusSet.has(n.id);
          const r = (KIND_RADIUS[n.kind] ?? 4) + Math.min(4, n.degree / 6);
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`} opacity={dim ? 0.18 : 1} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} onClick={() => setSelected(n)} className="cursor-pointer">
              <circle r={r + 3} fill={PALETTE[n.community % PALETTE.length]} opacity="0.18" />
              <circle r={r} fill={PALETTE[n.community % PALETTE.length]} stroke="#0a0a14" strokeWidth="1" />
              {(n.kind === "file" || n.kind === "folder" || n.degree > 6 || focusSet?.has(n.id)) && <text x={r + 4} y={3} fontSize="9" fill="#cbd5e1" fontFamily="ui-monospace, monospace">{n.label}</text>}
            </g>
          );
        })}
      </svg>
      <aside className="rounded-2xl border bg-card p-3 text-xs" data-testid="graph-side">
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Selection</p>
        {selected ? (
          <div className="mt-2 space-y-1">
            <p className="text-sm font-semibold">{selected.label}</p>
            <p className="font-mono text-[11px] text-muted-foreground">{selected.file}{selected.line ? `:${selected.line}` : ""}</p>
            <p><span className="text-muted-foreground">Kind</span> {selected.kind} · <span className="text-muted-foreground">Degree</span> {selected.degree} · <span className="text-muted-foreground">Community</span> {selected.community}</p>
            <p className="text-muted-foreground">Connected to</p>
            <ul className="max-h-64 space-y-0.5 overflow-auto font-mono text-[11px]">
              {[...(neighbours.get(selected.id) ?? [])].slice(0, 40).map((id) => <li key={id} className="truncate">{nodes[index.get(id) ?? 0]?.label ?? id}</li>)}
            </ul>
          </div>
        ) : <p className="mt-2 text-muted-foreground">Hover to highlight a neighbourhood, click a node for details. Colours are communities found by label propagation; cyan edges are imports, pink edges are calls.</p>}
        <p className="mt-3 border-t pt-2 text-muted-foreground">{nodes.length} nodes · {edges.length} edges</p>
      </aside>
    </div>
  );
}
