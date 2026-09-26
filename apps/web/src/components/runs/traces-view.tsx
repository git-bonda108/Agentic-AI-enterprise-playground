"use client";

import { useEffect, useState } from "react";
import { Activity, Bot, MessageSquare, Waypoints } from "lucide-react";
import { formatTokens, formatUsd } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export type TraceItem = { kind: "run" | "sdk" | "chat"; id: string; title: string; status: string; source: string; started_at: string; steps: number; tokens: number; cost_usd: number; user_id: string; models?: string[] };
type TimelineItem = { type: "step" | "call" | "message"; at: string; node?: string; kind?: string; summary?: string; model?: string; provider?: string; tokens_in?: number; tokens_out?: number; cost_usd?: number; latency_ms?: number; status?: string; key_source?: string; role?: string; text?: string };
type TraceDetail = { kind: string; id: string; title: string; status: string; summary: { calls: number; tokens: number; cost_usd: number; latency_p50_ms: number; errors: number; models: string[] }; timeline: TimelineItem[]; started_at: string; finished_at: string | null; error?: string | null };

const KIND_ICON = { run: Bot, sdk: Waypoints, chat: MessageSquare } as const;
const STATUS_STYLE: Record<string, string> = { completed: "text-brand-emerald", failed: "text-brand-rose", error: "text-brand-rose", waiting_review: "text-brand-amber", running: "text-brand-cyan", queued: "text-muted-foreground" };
const pad = (n: number) => String(n).padStart(2, "0");
const when = (iso: string) => { const d = new Date(iso); return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}Z`; };
const clock = (iso: string) => { const d = new Date(iso); return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`; };

export function TracesView({ initial, scope, days: initialDays }: { initial: TraceItem[]; scope: string; days: number }) {
  const [days, setDays] = useState(initialDays);
  const [kind, setKind] = useState<"" | "run" | "sdk" | "chat">("");
  const [rows, setRows] = useState(initial);
  const [selected, setSelected] = useState<TraceItem | null>(null);
  const [detail, setDetail] = useState<TraceDetail | null>(null);

  useEffect(() => {
    let stale = false;
    fetch(`/api/pg/v1/traces?days=${days}&kind=${kind}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (j && !stale) setRows(j.traces); }).catch(() => {});
    return () => { stale = true; };
  }, [days, kind]);

  useEffect(() => {
    if (!selected) return;
    let stale = false;
    fetch(`/api/pg/v1/traces/${selected.kind}/${encodeURIComponent(selected.id)}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (j && !stale) setDetail(j); }).catch(() => {});
    return () => { stale = true; };
  }, [selected]);

  const shown = selected && detail && detail.id === selected.id ? detail : null;
  const maxLatency = Math.max(1, ...(shown?.timeline ?? []).map((t) => t.latency_ms ?? 0));

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Operate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Traces</h1>
          <p className="mt-1 text-sm text-muted-foreground">Every run, SDK session and chat as a timeline: each step beside the model calls it made, with model, tokens, cost, latency and which key paid. Scope: {scope}.</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <div role="tablist" aria-label="Kind" className="flex rounded-lg border bg-card p-0.5">
            {([["", "All"], ["run", "Runs"], ["sdk", "SDK"], ["chat", "Chats"]] as const).map(([k, label]) => (
              <button key={k} type="button" role="tab" aria-selected={kind === k} onClick={() => setKind(k)} className={cn("h-7 rounded-md px-2.5", kind === k && "bg-secondary text-secondary-foreground")}>{label}</button>
            ))}
          </div>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Window" className="h-8 rounded-lg border bg-card px-2">
            {[1, 7, 30, 90].map((d) => <option key={d} value={d}>{d} days</option>)}
          </select>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <div className="overflow-hidden rounded-2xl border bg-card">
          <table className="w-full text-xs" data-testid="traces-table">
            <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-3 py-2">Trace</th><th className="px-3 py-2">Status</th><th className="px-3 py-2 text-right">Steps</th><th className="px-3 py-2 text-right">Tokens</th><th className="px-3 py-2 text-right">Cost</th></tr>
            </thead>
            <tbody>
              {rows.map((t) => {
                const Icon = KIND_ICON[t.kind];
                return (
                  <tr key={`${t.kind}-${t.id}`} onClick={() => setSelected(t)} className={cn("cursor-pointer border-t hover:bg-muted/40", selected?.id === t.id && "bg-brand-violet/10")} data-testid={`trace-${t.kind}`}>
                    <td className="px-3 py-2"><p className="flex items-center gap-1.5 font-medium"><Icon className="size-3.5 text-brand-violet-soft" /> {t.title}</p><p className="font-mono text-[10px] text-muted-foreground">{t.kind} · {t.source} · {when(t.started_at)}</p></td>
                    <td className={cn("px-3 py-2", STATUS_STYLE[t.status] ?? "")}>{t.status.replace("_", " ")}</td>
                    <td className="px-3 py-2 text-right font-mono">{t.steps}</td>
                    <td className="px-3 py-2 text-right font-mono">{formatTokens(t.tokens)}</td>
                    <td className="px-3 py-2 text-right font-mono">{formatUsd(t.cost_usd)}</td>
                  </tr>
                );
              })}
              {rows.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">No traces in this window.</td></tr>}
            </tbody>
          </table>
        </div>

        <section className="rounded-2xl border bg-card p-4" aria-label="Trace detail" data-testid="trace-detail">
          {!selected && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Activity className="size-4" /> Pick a trace to see its timeline.</p>}
          {selected && !shown && <p className="text-sm text-muted-foreground">Loading…</p>}
          {shown && (
            <>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-sm font-semibold">{shown.title} <span className={cn("ml-1 text-xs font-normal", STATUS_STYLE[shown.status] ?? "")}>{shown.status.replace("_", " ")}</span></h2>
                <p className="font-mono text-[11px] text-muted-foreground">{shown.summary.calls} calls · {formatTokens(shown.summary.tokens)} tokens · {formatUsd(shown.summary.cost_usd)} · p50 {shown.summary.latency_p50_ms} ms{shown.summary.errors ? ` · ${shown.summary.errors} errors` : ""}</p>
              </div>
              {shown.error && <p className="mt-2 rounded-lg border border-brand-rose/40 bg-brand-rose/10 p-2 text-xs text-brand-rose">{shown.error}</p>}
              <ol className="mt-3 space-y-1.5" data-testid="trace-timeline">
                {shown.timeline.map((t, i) => (
                  <li key={i} className="grid grid-cols-[72px_1fr] gap-2 text-xs">
                    <span className="pt-0.5 font-mono text-[10px] text-muted-foreground">{t.at ? clock(t.at) : ""}</span>
                    {t.type === "step" && <div><span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", t.kind === "llm" ? "bg-brand-violet/15 text-brand-violet-soft" : t.kind === "human" ? "bg-brand-amber/15 text-brand-amber" : t.kind === "gate" ? "bg-brand-pink/15 text-brand-pink" : "bg-brand-cyan/15 text-brand-cyan")}>{t.node}</span> <span>{t.summary}</span></div>}
                    {t.type === "call" && (
                      <div>
                        <span className="font-mono">{t.model}</span> <span className="text-muted-foreground">· {t.tokens_in} in / {t.tokens_out} out · {formatUsd(t.cost_usd ?? 0)} · {t.latency_ms} ms · {t.key_source} key{t.status !== "ok" ? ` · ${t.status}` : ""}</span>
                        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full", t.status === "ok" ? "gradient-brand" : "bg-brand-rose")} style={{ width: `${Math.max(2, ((t.latency_ms ?? 0) / maxLatency) * 100)}%` }} /></div>
                      </div>
                    )}
                    {t.type === "message" && <div><span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground">{t.role}</span> <span className="text-muted-foreground">{t.text}</span></div>}
                  </li>
                ))}
              </ol>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
