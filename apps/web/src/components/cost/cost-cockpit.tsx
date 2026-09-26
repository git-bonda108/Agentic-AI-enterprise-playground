"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertTriangle, Coins, Route, TrendingUp, Zap } from "lucide-react";
import { formatTokens, formatUsd, type Breakdown } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const LAYERS: { id: string; label: string }[] = [
  { id: "department", label: "Department" }, { id: "user", label: "User" }, { id: "feature", label: "Feature" },
  { id: "model", label: "Model" }, { id: "provider", label: "Provider" }, { id: "key_source", label: "Key source" }, { id: "conversation", label: "Conversation" },
];

export function CostCockpit({ initial, initialDays }: { initial: Breakdown; initialDays: Breakdown }) {
  const [days, setDays] = useState(30);
  const [by, setBy] = useState("model");
  const [data, setData] = useState<Breakdown>(initial);
  const [daily, setDaily] = useState<Breakdown>(initialDays);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`/api/pg/v1/usage/breakdown?days=${days}&by=${by}`).then((r) => r.json()),
      fetch(`/api/pg/v1/usage/breakdown?days=${days}&by=day`).then((r) => r.json()),
    ]).then(([b, d]) => { if (!cancelled) { setData(b); setDaily(d); } }).catch(() => {});
    return () => { cancelled = true; };
  }, [days, by]);

  const loading = data.by !== by || data.days !== days;
  const t = data.totals;
  const errorRate = t.requests ? Math.round((t.errors / t.requests) * 100) : 0;
  const maxCost = Math.max(...data.rows.map((r) => r.cost_usd), 0.000001);
  const chart = daily.rows.map((r) => ({ day: r.label.slice(5), cost: Number(r.cost_usd.toFixed(4)), requests: r.requests }));

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Operate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Cost</h1>
          <p className="mt-1 text-sm text-muted-foreground">{data.scope === "organization" ? "Organization-wide" : "Your own usage"}, reconciled to the ledger row by row.</p>
        </div>
        <div role="group" aria-label="Window" className="flex rounded-lg border bg-card p-0.5 text-xs">
          {[7, 30, 90].map((d) => (
            <button key={d} type="button" aria-pressed={days === d} onClick={() => setDays(d)} className={cn("h-7 rounded-md px-2.5", days === d && "bg-secondary text-secondary-foreground")}>{d} days</button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi icon={Coins} label="Spend this month" value={formatUsd(t.spend_month_usd)} foot={`${formatUsd(t.cost_usd)} in window`} />
        <Kpi icon={TrendingUp} label="Forecast this month" value={formatUsd(t.forecast_month_usd)} foot="Straight-line from month to date" />
        <Kpi icon={Route} label="Saved by Smart routing" value={formatUsd(t.savings_usd)} foot={`${t.routed_requests} routed requests`} accent="text-brand-emerald" />
        <Kpi icon={Zap} label="Tokens" value={formatTokens(t.tokens)} foot={`${t.requests} requests`} />
        <Kpi icon={AlertTriangle} label="Error rate" value={`${errorRate}%`} foot={`${t.errors} failed or blocked`} accent={errorRate > 10 ? "text-brand-rose" : "text-brand-amber"} />
      </div>

      <div className="mt-5 rounded-2xl border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">Spend by day</p>
        <div className="mt-2 h-44" aria-label="Spend by day chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ top: 6, right: 6, bottom: 0, left: 0 }} accessibilityLayer={false}>
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} width={64} tickFormatter={(v) => `$${v}`} />
              <Tooltip cursor={{ fill: "color-mix(in oklch, var(--brand-violet) 12%, transparent)" }} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} formatter={(v) => [formatUsd(Number(v)), "spend"]} />
              <Bar dataKey="cost" fill="var(--brand-violet-soft)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border bg-card">
        <div className="flex flex-wrap items-center gap-1 border-b p-2" role="tablist" aria-label="Cost layer">
          {LAYERS.map((l) => (
            <button key={l.id} type="button" role="tab" aria-selected={by === l.id} onClick={() => setBy(l.id)} className={cn("h-8 rounded-lg px-3 text-xs", by === l.id ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground")}>{l.label}</button>
          ))}
          {loading && <span className="ml-auto pr-2 text-[11px] text-muted-foreground">Refreshing…</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="cost-table">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-3 py-2">{LAYERS.find((l) => l.id === by)?.label}</th><th className="px-3 py-2 w-1/3">Share</th><th className="px-3 py-2 text-right">Cost</th><th className="px-3 py-2 text-right">Tokens</th><th className="px-3 py-2 text-right">Requests</th><th className="px-3 py-2 text-right">Errors</th><th className="px-3 py-2 text-right">Saved</th><th className="px-3 py-2 text-right">Avg latency</th></tr>
            </thead>
            <tbody>
              {data.rows.length === 0 && <tr><td colSpan={8} className="px-3 py-8 text-center text-muted-foreground">No usage in this window yet.</td></tr>}
              {data.rows.map((r) => (
                <tr key={r.key} className="border-t">
                  <td className="max-w-[280px] truncate px-3 py-2 font-medium" title={r.label}>{r.label}</td>
                  <td className="px-3 py-2"><span className="block h-1.5 w-full overflow-hidden rounded-full bg-muted"><span className="block h-full rounded-full gradient-brand" style={{ width: `${Math.max(2, (r.cost_usd / maxCost) * 100)}%` }} /></span></td>
                  <td className="px-3 py-2 text-right font-mono">{formatUsd(r.cost_usd)}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatTokens(r.tokens_in + r.tokens_out)}</td>
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
    </div>
  );
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
