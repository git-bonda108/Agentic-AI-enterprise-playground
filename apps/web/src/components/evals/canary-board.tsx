"use client";

import { useState } from "react";
import { Loader2, Play, Radar, RotateCcw, ShieldAlert } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { HardeningLadder } from "@/components/evals/hardening-ladder";
import type { AlertItem, CanaryBoardRow, EvalRunRecord } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export function CanaryBoard({ rows: initial, history: initialHistory, alerts: initialAlerts, isAdmin }: { rows: CanaryBoardRow[]; history: Record<string, EvalRunRecord[]>; alerts: AlertItem[]; isAdmin: boolean }) {
  const [rows, setRows] = useState(initial);
  const [history, setHistory] = useState(initialHistory);
  const [alerts, setAlerts] = useState(initialAlerts);
  const [selected, setSelected] = useState<string | null>(initial[0]?.suite_id ?? null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = async () => {
    const res = await fetch("/api/pg/v1/evals/canary");
    if (res.ok) {
      const list = (await res.json()).canaries as CanaryBoardRow[];
      setRows(list);
      const hist: Record<string, EvalRunRecord[]> = {};
      await Promise.all(list.map(async (c) => { const r = await fetch(`/api/pg/v1/evals/runs?suite_id=${c.suite_id}&kind=canary&limit=30`); if (r.ok) hist[c.suite_id] = ((await r.json()).runs as EvalRunRecord[]).reverse(); }));
      setHistory(hist);
    }
    const a = await fetch("/api/pg/v1/alerts");
    if (a.ok) setAlerts((await a.json()).alerts);
    window.dispatchEvent(new Event("playground:alerts"));
  };
  const runNow = async (c: CanaryBoardRow) => {
    setBusy(c.suite_id);
    const res = await fetch(`/api/pg/v1/evals/suites/${c.suite_id}/canary/run?wait=true`, { method: "POST" });
    setBusy(null);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "Canary failed to start"); return; }
    const r = (await res.json()) as EvalRunRecord;
    if (r.drift?.verdict === "drift") toast.error(`Drift: ${r.drift.reasons.join("; ")}`); else toast.success(`Stable: ${r.summary.pass_rate}% pass rate`);
    refresh();
  };
  const toggle = async (c: CanaryBoardRow, field: "enabled" | "auto_rollback") => {
    const res = await fetch(`/api/pg/v1/evals/suites/${c.suite_id}/canary`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ enabled: field === "enabled" ? !c.enabled : c.enabled, hour_utc: c.hour_utc, auto_rollback: field === "auto_rollback" ? !c.auto_rollback : c.auto_rollback, max_pass_rate_drop: c.max_pass_rate_drop, max_cost_increase_pct: c.max_cost_increase_pct, max_latency_increase_pct: c.max_latency_increase_pct }) });
    if (res.ok) refresh();
  };
  const tick = async () => {
    setBusy("tick");
    const res = await fetch("/api/pg/v1/evals/canary/tick?force=true&wait=true", { method: "POST" });
    setBusy(null);
    if (res.ok) { toast.success(`Ran ${(await res.json()).started.length} canaries`); refresh(); }
  };

  const current = rows.find((r) => r.suite_id === selected) ?? null;
  const series = (selected ? history[selected] ?? [] : []).filter((r) => r.status === "completed").map((r, i) => ({ i: i + 1, pass: r.summary.pass_rate ?? 0, cost: Number(((r.summary.cost_per_case_usd ?? 0) * 100).toFixed(4)) }));
  const canaryAlerts = alerts.filter((a) => a.kind === "canary");

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Evaluate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Canary</h1>
          <p className="mt-1 text-sm text-muted-foreground">Nightly reruns of every scheduled suite, compared with the last good run. Drift raises an alert, demotes the agent a level, and rolls a wizard agent back to its last good version.</p>
        </div>
        {isAdmin && <Button variant="outline" onClick={tick} disabled={busy !== null} aria-label="Run all canaries now">{busy === "tick" ? <Loader2 className="size-4 animate-spin" /> : <Radar className="size-4" />} Run all now</Button>}
      </div>

      <div className="mt-5 overflow-hidden rounded-2xl border bg-card">
        <table className="w-full text-xs" data-testid="canary-table">
          <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr><th className="px-3 py-2">Suite</th><th className="px-3 py-2">Agent</th><th className="px-3 py-2">Level</th><th className="px-3 py-2">Schedule</th><th className="px-3 py-2">Last run</th><th className="px-3 py-2">Streak</th><th className="px-3 py-2">Rollback</th><th className="px-3 py-2"></th></tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className={cn("cursor-pointer border-t", selected === c.suite_id && "bg-brand-violet/5")} onClick={() => setSelected(c.suite_id)}>
                <td className="px-3 py-2 font-medium">{c.suite?.name ?? c.suite_id}</td>
                <td className="px-3 py-2 text-muted-foreground">{c.suite?.blueprint_name}</td>
                <td className="px-3 py-2">{c.hardening ? <span className="rounded-md bg-brand-violet/15 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">L{c.hardening.level} {c.hardening.name}</span> : null}</td>
                <td className="px-3 py-2"><button type="button" onClick={(e) => { e.stopPropagation(); toggle(c, "enabled"); }} aria-label={`${c.enabled ? "Pause" : "Enable"} canary for ${c.suite?.name ?? c.suite_id}`} className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", c.enabled ? "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300" : "bg-muted text-muted-foreground")}>{c.enabled ? `nightly ${String(c.hour_utc).padStart(2, "0")}:00 UTC` : "paused"}</button></td>
                <td className="px-3 py-2">{c.last_run ? <span className={cn("font-mono", c.last_run.drift?.verdict === "drift" || !c.last_run.summary.gate_passed ? "text-brand-rose" : "text-brand-emerald")}>{c.last_run.summary.pass_rate ?? "…"}% {c.last_run.drift?.verdict === "drift" ? "drift" : c.last_run.status === "completed" ? "stable" : c.last_run.status}</span> : <span className="text-muted-foreground">never</span>}</td>
                <td className="px-3 py-2 font-mono">{c.consecutive_passes}</td>
                <td className="px-3 py-2"><button type="button" onClick={(e) => { e.stopPropagation(); toggle(c, "auto_rollback"); }} aria-label={`Toggle automatic rollback for ${c.suite?.name ?? c.suite_id}`} className="inline-flex items-center gap-1 text-[11px]"><RotateCcw className="size-3" /> {c.auto_rollback ? "automatic" : "manual"}</button></td>
                <td className="px-3 py-2 text-right"><Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); runNow(c); }} disabled={busy !== null} aria-label={`Run canary now for ${c.suite?.name ?? c.suite_id}`}>{busy === c.suite_id ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />} Run now</Button></td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={8} className="px-3 py-6 text-center text-muted-foreground">No canaries yet. Enable one from a suite on the Evals page.</td></tr>}
          </tbody>
        </table>
      </div>

      {current && (
        <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-2xl border bg-card p-4">
            <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Pass rate and cost per case over canary runs · {current.suite?.name}</p>
            {series.length === 0 ? <p className="mt-3 text-xs text-muted-foreground">No completed canary runs yet.</p> : (
              <div className="mt-2 h-56" data-testid="drift-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 0 }} accessibilityLayer={false}>
                    <XAxis dataKey="i" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <YAxis yAxisId="pass" domain={[0, 100]} width={36} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <YAxis yAxisId="cost" orientation="right" width={44} tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" />
                    <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12 }} formatter={(v, name) => [name === "cost" ? `${v}¢` : `${v}%`, name === "cost" ? "cost per case" : "pass rate"]} />
                    <Line yAxisId="pass" type="monotone" dataKey="pass" stroke="var(--brand-emerald)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                    <Line yAxisId="cost" type="monotone" dataKey="cost" stroke="var(--brand-pink)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            {current.hardening && <div className="mt-4"><HardeningLadder ladder={current.hardening} /></div>}
          </div>
          <div className="rounded-2xl border bg-card p-4">
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground"><ShieldAlert className="size-3.5" /> Drift events</p>
            <ul className="mt-2 space-y-2 text-xs" data-testid="drift-events">
              {canaryAlerts.map((a) => (
                <li key={a.id} className="rounded-xl border p-2.5">
                  <p className="font-medium">{a.label}</p>
                  <p className="mt-0.5 text-muted-foreground">{a.message}</p>
                  <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">{new Date(a.created_at).toLocaleString()} · pass rate {a.spend_usd}% vs baseline {a.cap_usd}%</p>
                </li>
              ))}
              {canaryAlerts.length === 0 && <li className="text-muted-foreground">No drift detected so far.</li>}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
