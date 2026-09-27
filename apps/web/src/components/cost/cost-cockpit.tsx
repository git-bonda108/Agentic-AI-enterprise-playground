"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, Coins, Download, Layers, Route, TrendingUp, X, Zap } from "lucide-react";
import { formatTokens, formatUsd, type Breakdown, type LedgerPage } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const LAYERS: { id: string; label: string; param: string; next: string }[] = [
  { id: "department", label: "Department", param: "department", next: "user" },
  { id: "user", label: "User", param: "user_id", next: "feature" },
  { id: "feature", label: "Feature", param: "feature", next: "model" },
  { id: "model", label: "Model", param: "model", next: "conversation" },
  { id: "provider", label: "Provider", param: "provider", next: "model" },
  { id: "key_source", label: "Key source", param: "key_source", next: "model" },
  { id: "blueprint", label: "Blueprint", param: "blueprint_id", next: "model" },
  { id: "conversation", label: "Conversation", param: "conversation_id", next: "model" },
];
const DAY_LAYER = { id: "day", label: "Day", param: "day", next: "feature" };

type Filter = { param: string; value: string; label: string; layer: string };

function query(days: number, filters: Filter[], extra: Record<string, string | number>): string {
  const q = new URLSearchParams({ days: String(days) });
  for (const f of filters) q.set(f.param, f.value);
  for (const [k, v] of Object.entries(extra)) q.set(k, String(v));
  return q.toString();
}

function Kpi({ icon: Icon, label, value, foot, accent = "text-brand-violet-soft" }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string; foot: string; accent?: string }) {
  return (
    <div className="card-hover rounded-2xl border bg-card p-4">
      <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground"><Icon className={`size-3.5 ${accent}`} /> {label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
      <p className="mt-1 text-[11px] text-muted-foreground">{foot}</p>
    </div>
  );
}

function TokenBar({ tokensIn, tokensOut, cached }: { tokensIn: number; tokensOut: number; cached: number }) {
  const total = Math.max(tokensIn + tokensOut, 1);
  const cachedPct = Math.min((cached / total) * 100, 100);
  const inPct = Math.max((tokensIn / total) * 100 - cachedPct, 0);
  const outPct = (tokensOut / total) * 100;
  return (
    <span className="flex h-1.5 w-full overflow-hidden rounded-full bg-muted" title={`${formatTokens(tokensIn)} in (${formatTokens(cached)} cached) · ${formatTokens(tokensOut)} out`}>
      <span className="h-full bg-brand-emerald" style={{ width: `${cachedPct}%` }} />
      <span className="h-full bg-brand-cyan" style={{ width: `${inPct}%` }} />
      <span className="h-full bg-brand-violet-soft" style={{ width: `${outPct}%` }} />
    </span>
  );
}

export function CostCockpit({ initial, initialDays }: { initial: Breakdown; initialDays: Breakdown }) {
  const [days, setDays] = useState(30);
  const [by, setBy] = useState("model");
  const [filters, setFilters] = useState<Filter[]>([]);
  const [data, setData] = useState<Breakdown>(initial);
  const [daily, setDaily] = useState<Breakdown>(initialDays);
  const [ledger, setLedger] = useState<LedgerPage | null>(null);
  const [ledgerLimit, setLedgerLimit] = useState(25);

  useEffect(() => {
    let stale = false;
    Promise.all([
      fetch(`/api/pg/v1/usage/breakdown?${query(days, filters, { by })}`).then((r) => r.json()),
      fetch(`/api/pg/v1/usage/breakdown?${query(days, filters, { by: "day" })}`).then((r) => r.json()),
    ]).then(([b, d]) => { if (!stale) { setData(b); setDaily(d); } }).catch(() => {});
    return () => { stale = true; };
  }, [days, by, filters]);

  useEffect(() => {
    let stale = false;
    fetch(`/api/pg/v1/usage/events?${query(days, filters, { limit: ledgerLimit })}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (!stale && j) setLedger(j); }).catch(() => {});
    return () => { stale = true; };
  }, [days, filters, ledgerLimit]);

  const layer = LAYERS.find((l) => l.id === by) ?? DAY_LAYER;
  const loading = data.by !== by || data.days !== days;
  const t = data.totals;
  const errorRate = t.requests ? Math.round((t.errors / t.requests) * 100) : 0;
  const maxCost = Math.max(...data.rows.map((r) => r.cost_usd), 0.000001);
  const chart = daily.rows.map((r) => ({ day: r.label.slice(5), cost: Number(r.cost_usd.toFixed(4)), requests: r.requests, key: r.key }));

  const drill = (key: string, label: string) => {
    if (key === "-" || filters.some((f) => f.param === layer.param)) return;
    setFilters([...filters, { param: layer.param, value: key, label, layer: layer.label }]);
    setBy(layer.next);
    setLedgerLimit(25);
  };
  const remove = (param: string) => setFilters(filters.filter((f) => f.param !== param));

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Operate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Cost</h1>
          <p className="mt-1 text-sm text-muted-foreground">{data.scope === "organization" ? "Organization-wide" : "Your own usage"}, reconciled to the ledger row by row. Click a row to drill one layer down.</p>
        </div>
        <div role="group" aria-label="Window" className="flex rounded-lg border bg-card p-0.5 text-xs">
          {[7, 30, 90].map((d) => (
            <button key={d} type="button" aria-pressed={days === d} onClick={() => setDays(d)} className={cn("h-7 rounded-md px-2.5", days === d && "bg-secondary text-secondary-foreground")}>{d} days</button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs" data-testid="cost-filters" aria-label="Active filters">
        <span className="text-muted-foreground">{filters.length === 0 ? "No filters: the whole window." : "Filters:"}</span>
        {filters.map((f) => (
          <span key={f.param} className="inline-flex items-center gap-1 rounded-full border bg-card px-2 py-0.5">
            <span className="text-muted-foreground">{f.layer}</span> <span className="font-medium">{f.label}</span>
            <button type="button" onClick={() => remove(f.param)} aria-label={`Remove filter ${f.layer} ${f.label}`} className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"><X className="size-3" /></button>
          </span>
        ))}
        {filters.length > 0 && <button type="button" onClick={() => setFilters([])} className="text-brand-violet-soft hover:underline">Clear all</button>}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <Kpi icon={Coins} label="Spend this month" value={formatUsd(t.spend_month_usd)} foot={`${formatUsd(t.cost_usd)} in view`} />
        <Kpi icon={TrendingUp} label="Forecast this month" value={formatUsd(t.forecast_month_usd)} foot="Straight-line from month to date" />
        <Kpi icon={Route} label="Saved by Smart routing" value={formatUsd(t.savings_usd)} foot={`${t.routed_requests} routed requests`} accent="text-brand-emerald" />
        <Kpi icon={Zap} label="Tokens" value={formatTokens(t.tokens)} foot={`${t.requests} requests`} />
        <Kpi icon={Layers} label="Token split" value={`${formatTokens(t.tokens_in)} in`} foot={`${formatTokens(t.tokens_out)} out · ${formatTokens(t.tokens_cached)} cached`} accent="text-brand-cyan" />
        <Kpi icon={AlertTriangle} label="Error rate" value={`${errorRate}%`} foot={`${t.errors} failed or blocked`} accent={errorRate > 10 ? "text-brand-rose" : "text-brand-amber"} />
      </div>

      <div className="mt-5 rounded-2xl border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">Spend by day{filters.length > 0 ? " (filtered)" : ""}. Click a bar to filter by that day.</p>
        <div className="mt-2 h-44" aria-label="Spend by day chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ top: 6, right: 6, bottom: 0, left: 0 }} accessibilityLayer={false} onClick={(s) => { const idx = Number((s as { activeIndex?: number | string } | null)?.activeIndex); const p = Number.isFinite(idx) ? chart[idx] : undefined; if (p?.key && !filters.some((f) => f.param === "day")) { setFilters([...filters, { param: "day", value: p.key, label: p.key, layer: "Day" }]); } }}>
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} width={64} tickFormatter={(v) => `$${v}`} />
              <Tooltip cursor={{ fill: "color-mix(in oklch, var(--brand-violet) 12%, transparent)" }} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} formatter={(v) => [formatUsd(Number(v)), "spend"]} />
              <Bar dataKey="cost" fill="var(--brand-violet-soft)" radius={[4, 4, 0, 0]} isAnimationActive={false} className="cursor-pointer" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border bg-card">
        <div className="flex flex-wrap items-center gap-1 border-b p-2" role="tablist" aria-label="Cost layer">
          {LAYERS.map((l) => (
            <button key={l.id} type="button" role="tab" aria-selected={by === l.id} onClick={() => setBy(l.id)} className={cn("h-8 rounded-lg px-3 text-xs", by === l.id ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground")}>{l.label}</button>
          ))}
          <span className="ml-auto flex items-center gap-2 pr-2 text-[11px] text-muted-foreground">
            {loading && <span>Refreshing…</span>}
            <a href={`/api/pg/v1/usage/breakdown?${query(days, filters, { by, format: "csv" })}`} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 hover:bg-muted" data-testid="export-breakdown"><Download className="size-3" /> Export CSV</a>
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="cost-table">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-3 py-2">{layer.label}</th><th className="px-3 py-2 w-1/4">Share</th><th className="px-3 py-2 text-right">Cost</th><th className="px-3 py-2 text-right">Tokens</th><th className="px-3 py-2 w-28">In · out · cached</th><th className="px-3 py-2 text-right">Requests</th><th className="px-3 py-2 text-right">Errors</th><th className="px-3 py-2 text-right">Saved</th><th className="px-3 py-2 text-right">Avg latency</th></tr>
            </thead>
            <tbody>
              {data.rows.length === 0 && <tr><td colSpan={9} className="px-3 py-8 text-center text-muted-foreground">No usage in this view yet.</td></tr>}
              {data.rows.map((r) => (
                <tr key={r.key} className={cn("border-t", r.key !== "-" && "cursor-pointer hover:bg-muted/50")} onClick={() => drill(r.key, r.label)} role={r.key !== "-" ? "button" : undefined} tabIndex={r.key !== "-" ? 0 : undefined} onKeyDown={(e) => { if (e.key === "Enter") drill(r.key, r.label); }} aria-label={r.key !== "-" ? `Drill into ${r.label}` : undefined}>
                  <td className="max-w-[280px] truncate px-3 py-2 font-medium" title={r.label}>{r.label}</td>
                  <td className="px-3 py-2"><span className="block h-1.5 w-full overflow-hidden rounded-full bg-muted"><span className="block h-full rounded-full gradient-brand" style={{ width: `${Math.max(2, (r.cost_usd / maxCost) * 100)}%` }} /></span></td>
                  <td className="px-3 py-2 text-right font-mono">{formatUsd(r.cost_usd)}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatTokens(r.tokens_in + r.tokens_out)}</td>
                  <td className="px-3 py-2"><TokenBar tokensIn={r.tokens_in} tokensOut={r.tokens_out} cached={r.tokens_cached} /></td>
                  <td className="px-3 py-2 text-right font-mono">{r.requests}</td>
                  <td className={cn("px-3 py-2 text-right font-mono", r.errors > 0 && "text-brand-rose")}>{r.errors}</td>
                  <td className="px-3 py-2 text-right font-mono text-brand-emerald">{r.savings_usd > 0 ? formatUsd(r.savings_usd) : "—"}</td>
                  <td className="px-3 py-2 text-right font-mono">{(r.avg_latency_ms / 1000).toFixed(1)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border bg-card" data-testid="ledger">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b p-3">
          <div>
            <p className="text-sm font-semibold">Ledger rows</p>
            <p className="text-[11px] text-muted-foreground">The raw calls behind this view, newest first{ledger ? `: ${ledger.total} in the window` : ""}.</p>
          </div>
          <a href={`/api/pg/v1/usage/events?${query(days, filters, { format: "csv" })}`} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted" data-testid="export-ledger"><Download className="size-3" /> Export rows</a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="ledger-table">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-3 py-2">When</th><th className="px-3 py-2">User</th><th className="px-3 py-2">Feature</th><th className="px-3 py-2">Model</th><th className="px-3 py-2 text-right">In</th><th className="px-3 py-2 text-right">Out</th><th className="px-3 py-2 text-right">Cached</th><th className="px-3 py-2 text-right">Cost</th><th className="px-3 py-2 text-right">Latency</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Key</th><th className="px-3 py-2">Context</th></tr>
            </thead>
            <tbody>
              {(ledger?.rows ?? []).length === 0 && <tr><td colSpan={12} className="px-3 py-6 text-center text-muted-foreground">No ledger rows in this view.</td></tr>}
              {(ledger?.rows ?? []).map((e) => (
                <tr key={e.id} className="border-t">
                  <td className="whitespace-nowrap px-3 py-1.5 font-mono text-[11px]">{e.created_at.replace("T", " ").slice(0, 19)}</td>
                  <td className="max-w-[140px] truncate px-3 py-1.5" title={e.department}>{e.user}</td>
                  <td className="px-3 py-1.5">{e.feature}</td>
                  <td className="max-w-[180px] truncate px-3 py-1.5 font-mono text-[11px]" title={e.provider}>{e.model}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{e.tokens_in}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{e.tokens_out}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{e.tokens_cached}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{formatUsd(e.cost_usd)}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{(e.latency_ms / 1000).toFixed(1)}s</td>
                  <td className={cn("px-3 py-1.5", e.status !== "ok" && "text-brand-rose")}>{e.status}</td>
                  <td className="px-3 py-1.5">{e.key_source === "personal" ? "yours" : e.key_source}{e.routed ? " · smart" : ""}</td>
                  <td className="max-w-[200px] truncate px-3 py-1.5 text-muted-foreground" title={e.trace_id ?? ""}>{e.blueprint || e.conversation || (e.trace_id ? `trace ${e.trace_id.slice(0, 8)}` : "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {ledger && ledger.total > ledger.rows.length && (
          <div className="border-t p-2 text-center">
            <button type="button" onClick={() => setLedgerLimit(ledgerLimit + 50)} className="text-xs text-brand-violet-soft hover:underline">Show more ({ledger.total - ledger.rows.length} left)</button>
          </div>
        )}
      </div>
    </div>
  );
}
