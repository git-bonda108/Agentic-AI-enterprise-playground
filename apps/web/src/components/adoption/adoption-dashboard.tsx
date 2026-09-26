"use client";

import { useState } from "react";
import { Bar, BarChart, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Clock, Coins, Loader2, Sparkles, Target, TrendingUp, Users } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/playground/markdown";
import type { AdoptionSummary, RunRecord } from "@/lib/playground-types";
import { formatUsd } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export function AdoptionDashboard({ initial, isAdmin }: { initial: AdoptionSummary; isAdmin: boolean }) {
  const [data, setData] = useState(initial);
  const [days, setDays] = useState(initial.days);
  const [digest, setDigest] = useState<RunRecord | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, number>>({});

  const reload = async (d: number) => {
    setDays(d);
    const res = await fetch(`/api/pg/v1/adoption/summary?days=${d}`);
    if (res.ok) setData(await res.json());
  };
  const saveAssumptions = async () => {
    setBusy("save");
    const res = await fetch("/api/pg/v1/adoption/assumptions", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ values: edits }) });
    setBusy(null);
    if (!res.ok) { toast.error("Could not save"); return; }
    setEdits({});
    toast.success("Assumptions updated; every number below recalculated");
    reload(days);
  };
  const runDigest = async () => {
    setBusy("digest");
    const res = await fetch("/api/pg/v1/adoption/digest", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ days, audience: "team leads" }) });
    setBusy(null);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "The digest agent failed"); return; }
    setDigest(await res.json());
  };

  const k = data.kpis;
  const kpis = [
    { icon: Users, label: "Active people", value: `${k.active_users} of ${k.total_users}`, accent: "text-brand-violet-soft", foot: "" },
    { icon: Clock, label: "Hours in the playground", value: k.hours.toFixed(1), accent: "text-brand-cyan", foot: "" },
    { icon: Target, label: "Outcomes", value: String(k.outcomes), accent: "text-brand-pink", foot: k.cost_per_outcome_usd !== null ? `${formatUsd(k.cost_per_outcome_usd)} per outcome` : "" },
    { icon: Coins, label: "Model spend", value: formatUsd(k.cost_usd), accent: "text-brand-amber", foot: "" },
    { icon: TrendingUp, label: "Hours saved (est.)", value: k.hours_saved.toFixed(1), accent: "text-brand-emerald", foot: `${formatUsd(k.value_saved_usd)} value · ROI ${k.roi ?? "n/a"}×` },
  ];
  const digestOut = digest?.output as { digest_md?: string; recommendations?: { action: string; why: string; owner: string }[] } | null | undefined;

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Operate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Adoption</h1>
          <p className="mt-1 text-sm text-muted-foreground">Hours per feature, cost per outcome and an ROI matrix by department{data.department ? ` (${data.department})` : ""}. Every estimate shows the assumption behind it.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1" role="tablist" aria-label="Window">{[7, 30, 90].map((d) => <button key={d} type="button" role="tab" aria-selected={days === d} onClick={() => reload(d)} className={cn("h-8 rounded-lg border px-2.5 text-xs", days === d ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground")}>{d} days</button>)}</div>
          <Button className="glow-violet" onClick={runDigest} disabled={busy !== null} aria-label="Generate digest">{busy === "digest" ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />} Generate digest</Button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5" data-testid="adoption-kpis">
        {kpis.map((c) => (
          <div key={c.label} className="rounded-2xl border bg-card p-4">
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground"><c.icon className={cn("size-3.5", c.accent)} /> {c.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight">{c.value}</p>
            {c.foot && <p className="mt-1 text-[11px] text-muted-foreground">{c.foot}</p>}
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <section className="rounded-2xl border bg-card p-4" aria-label="Hours per feature">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Hours per feature · used (violet) and saved, estimated (green)</p>
          <div className="mt-2 h-56" data-testid="hours-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.features} margin={{ top: 6, right: 6, bottom: 0, left: 0 }} accessibilityLayer={false}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} stroke="var(--muted-foreground)" interval={0} />
                <YAxis width={40} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                <Tooltip cursor={{ fill: "color-mix(in oklch, var(--brand-violet) 12%, transparent)" }} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} formatter={(v, name) => [`${v} h`, name === "hours_saved" ? "saved (est.)" : "used"]} />
                <Bar dataKey="hours" fill="var(--brand-violet)" radius={[6, 6, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="hours_saved" fill="var(--brand-emerald)" radius={[6, 6, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="mt-3 w-full text-xs" data-testid="feature-table">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground"><tr><th className="py-1">Feature</th><th className="text-right">People</th><th className="text-right">Hours</th><th className="text-right">Outcomes</th><th className="text-right">Cost/outcome</th><th className="text-right">Saved (est.)</th></tr></thead>
            <tbody>{data.features.map((f) => <tr key={f.feature} className="border-t"><td className="py-1.5">{f.label}</td><td className="text-right font-mono">{f.users}</td><td className="text-right font-mono">{f.hours}</td><td className="text-right font-mono">{f.outcomes}</td><td className="text-right font-mono">{f.cost_per_outcome_usd === null ? "–" : formatUsd(f.cost_per_outcome_usd)}</td><td className="text-right font-mono">{f.hours_saved} h · {formatUsd(f.value_saved_usd)}</td></tr>)}</tbody>
          </table>
        </section>

        <section className="rounded-2xl border bg-card p-4" aria-label="Weekly activity">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Requests and people per week</p>
          <div className="mt-2 h-56">
            {data.weekly.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.weekly} margin={{ top: 6, right: 12, bottom: 0, left: 0 }} accessibilityLayer={false}>
                  <XAxis dataKey="week" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                  <YAxis yAxisId="r" width={36} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                  <YAxis yAxisId="u" orientation="right" width={30} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                  <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} />
                  <Line yAxisId="r" type="monotone" dataKey="requests" stroke="var(--brand-cyan)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                  <Line yAxisId="u" type="monotone" dataKey="users" stroke="var(--brand-pink)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="text-xs text-muted-foreground">No activity in this window.</p>}
          </div>
          <p className="mt-3 text-[11px] text-muted-foreground">{data.method}</p>
        </section>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <section className="overflow-hidden rounded-2xl border bg-card" aria-label="ROI by department">
          <table className="w-full text-xs" data-testid="roi-matrix">
            <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground"><tr><th className="px-3 py-2">Department</th><th className="px-3 py-2 text-right">People</th><th className="px-3 py-2 text-right">Hours</th><th className="px-3 py-2 text-right">Outcomes</th><th className="px-3 py-2 text-right">Spend</th><th className="px-3 py-2 text-right">Saved (est.)</th><th className="px-3 py-2 text-right">Value</th><th className="px-3 py-2 text-right">ROI</th></tr></thead>
            <tbody>
              {data.departments.map((d) => <tr key={d.department} className="border-t"><td className="px-3 py-2 font-medium">{d.department}</td><td className="px-3 py-2 text-right font-mono">{d.users}</td><td className="px-3 py-2 text-right font-mono">{d.hours}</td><td className="px-3 py-2 text-right font-mono">{d.outcomes}</td><td className="px-3 py-2 text-right font-mono">{formatUsd(d.cost_usd)}</td><td className="px-3 py-2 text-right font-mono">{d.hours_saved} h</td><td className="px-3 py-2 text-right font-mono">{formatUsd(d.value_saved_usd)}</td><td className="px-3 py-2 text-right font-mono">{d.roi === null ? "–" : `${d.roi}×`}</td></tr>)}
              {data.departments.length === 0 && <tr><td colSpan={8} className="px-3 py-6 text-center text-muted-foreground">No activity in this window.</td></tr>}
            </tbody>
          </table>
        </section>

        <section className="rounded-2xl border bg-card p-4 text-xs" aria-label="Assumptions" data-testid="assumptions">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Assumptions behind the estimates</p>
          <ul className="mt-2 space-y-1.5">
            {data.assumptions.map((a) => (
              <li key={a.key} className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">{a.label}</span>
                {isAdmin ? <input type="number" step={1} min={0} value={edits[a.key] ?? a.value} onChange={(e) => setEdits({ ...edits, [a.key]: Number(e.target.value) })} aria-label={a.label} className="h-7 w-20 rounded-lg border bg-background px-2 text-right font-mono" /> : <span className="font-mono">{a.value}</span>}
              </li>
            ))}
          </ul>
          {isAdmin && <Button size="sm" className="mt-3" onClick={saveAssumptions} disabled={busy !== null || Object.keys(edits).length === 0} aria-label="Save assumptions">{busy === "save" ? "Saving…" : "Save and recalculate"}</Button>}
        </section>
      </div>

      {digest && digestOut && (
        <section className="mt-4 rounded-2xl border bg-card p-4" aria-label="Adoption digest" data-testid="digest">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="flex items-center gap-1.5 text-sm font-semibold"><Sparkles className="size-4 text-brand-violet-soft" /> Digest by the Adoption digest agent</p>
            <a href={`/operate/runs/${digest.id}`} className="text-xs text-brand-violet-soft hover:underline">Open run · {formatUsd(digest.cost_usd)}</a>
          </div>
          <div className="mt-3 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
            <div className="text-sm"><Markdown text={digestOut.digest_md ?? ""} /></div>
            <ol className="space-y-2 text-xs">
              {(digestOut.recommendations ?? []).map((r, i) => <li key={i} className="rounded-xl border p-2.5"><p className="font-medium">{r.action}</p><p className="mt-0.5 text-muted-foreground">{r.why}</p><p className="mt-0.5 font-mono text-[10px] text-muted-foreground">owner: {r.owner}</p></li>)}
            </ol>
          </div>
        </section>
      )}
    </div>
  );
}
