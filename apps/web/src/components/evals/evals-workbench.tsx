"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2, Play, Plus, Radar, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { SuiteBuilder } from "@/components/evals/suite-builder";
import { HardeningLadder } from "@/components/evals/hardening-ladder";
import type { EvalLibrary, EvalRunRecord, EvalSuiteRecord, RunRecord } from "@/lib/playground-types";
import { formatUsd } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type AgentOption = { id: string; name: string; samples: { name: string; input: Record<string, unknown> }[] };

export function EvalsWorkbench({ suites: initial, library, agents, recentRuns, initialDetail, initialRuns, initialActive }: { suites: EvalSuiteRecord[]; library: EvalLibrary; agents: AgentOption[]; recentRuns: RunRecord[]; initialDetail: EvalSuiteRecord | null; initialRuns: EvalRunRecord[]; initialActive: EvalRunRecord | null }) {
  const router = useRouter();
  const [suites, setSuites] = useState(initial);
  const [detail, setDetail] = useState<EvalSuiteRecord | null>(initialDetail);
  const [runs, setRuns] = useState<EvalRunRecord[]>(initialRuns);
  const [active, setActive] = useState<EvalRunRecord | null>(initialActive);
  const [building, setBuilding] = useState(false);
  const [starting, setStarting] = useState(false);
  const [filter, setFilter] = useState("");

  const openRun = async (id: string) => {
    const res = await fetch(`/api/pg/v1/evals/runs/${id}`);
    if (res.ok) setActive(await res.json());
  };
  const load = async (id: string) => {
    const [s, r] = await Promise.all([fetch(`/api/pg/v1/evals/suites/${id}`), fetch(`/api/pg/v1/evals/runs?suite_id=${id}&limit=20`)]);
    if (s.ok) setDetail(await s.json());
    if (r.ok) { const list = (await r.json()).runs as EvalRunRecord[]; setRuns(list); if (list[0]) openRun(list[0].id); else setActive(null); }
  };
  const select = (s: EvalSuiteRecord) => { router.replace(`/evaluate/evals?suite=${s.id}`); load(s.id); };

  const inFlight = active !== null && (active.status === "running" || active.status === "queued");
  const activeId = active?.id;
  const detailId = detail?.id;
  useEffect(() => {
    if (!inFlight || !activeId) return;
    const t = setInterval(async () => {
      const res = await fetch(`/api/pg/v1/evals/runs/${activeId}`);
      if (!res.ok) return;
      const r = (await res.json()) as EvalRunRecord;
      setActive(r);
      if ((r.status === "completed" || r.status === "failed") && detailId) {
        const s = await fetch(`/api/pg/v1/evals/suites/${detailId}`);
        if (s.ok) setDetail(await s.json());
        const list = await fetch(`/api/pg/v1/evals/runs?suite_id=${detailId}&limit=20`);
        if (list.ok) setRuns((await list.json()).runs);
      }
    }, 1500);
    return () => clearInterval(t);
  }, [inFlight, activeId, detailId]);

  const start = async () => {
    if (!detail) return;
    setStarting(true);
    const res = await fetch(`/api/pg/v1/evals/suites/${detail.id}/run`, { method: "POST" });
    setStarting(false);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "Could not start"); return; }
    const r = (await res.json()) as EvalRunRecord;
    setRuns((list) => [r, ...list]);
    setActive(r);
  };
  const toggleCanary = async () => {
    if (!detail) return;
    const enabled = !(detail.canary?.enabled ?? false);
    const res = await fetch(`/api/pg/v1/evals/suites/${detail.id}/canary`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ enabled, hour_utc: detail.canary?.hour_utc ?? 2, auto_rollback: detail.canary?.auto_rollback ?? true }) });
    if (res.ok) { toast.success(enabled ? "Nightly canary enabled" : "Canary paused"); load(detail.id); }
  };

  const shown = suites.filter((s) => !filter || s.blueprint_name.toLowerCase().includes(filter.toLowerCase()) || s.name.toLowerCase().includes(filter.toLowerCase()));
  const criteriaNames = new Map(library.rubric.map((c) => [c.id, c.name]));

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Evaluate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Evals</h1>
          <p className="mt-1 text-sm text-muted-foreground">Golden sets, rubrics and gates for every agent. Each case runs for real and is metered; a judge model scores quality; the gate decides whether the agent climbs the hardening ladder.</p>
        </div>
        <Button className="glow-violet" onClick={() => setBuilding(true)} aria-label="Build a suite"><Plus className="size-4" /> Build a suite</Button>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-2" data-testid="suite-list">
          <input value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter suites" placeholder="Filter by agent or suite" className="h-8 w-full rounded-lg border bg-card px-2 text-xs" />
          {shown.map((s) => (
            <button key={s.id} type="button" onClick={() => select(s)} aria-label={`Open suite ${s.name}`} className={cn("card-hover w-full rounded-2xl border bg-card p-3 text-left", detail?.id === s.id && "border-brand-violet/60")}>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold">{s.name}</span>
                {s.last_run?.summary?.pass_rate !== undefined && <span className={cn("rounded-md px-1.5 py-0.5 font-mono text-[10px]", s.last_run.summary.gate_passed ? "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300" : "bg-brand-rose/15 text-rose-700 dark:text-rose-300")}>{s.last_run.summary.pass_rate}%</span>}
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">{s.blueprint_name} · {s.case_count} cases{s.system ? " · built in" : ""}{s.canary?.enabled ? " · canary" : ""}</p>
            </button>
          ))}
        </aside>

        <section className="min-w-0 space-y-4" data-testid="suite-detail">
          {!detail ? <div className="grid min-h-[320px] place-items-center rounded-2xl border bg-card text-sm text-muted-foreground">Select a suite, or build one.</div> : (
            <>
              <div className="rounded-2xl border bg-card p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">{detail.name}</h2>
                    <p className="text-xs text-muted-foreground">{detail.description || "No description"} · agent {detail.blueprint_name}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={toggleCanary} aria-label={detail.canary?.enabled ? "Pause canary" : "Enable nightly canary"}><Radar className="size-3.5" /> {detail.canary?.enabled ? "Canary on" : "Enable canary"}</Button>
                    <Button size="sm" className="glow-violet" onClick={start} disabled={starting || inFlight} aria-label="Run suite">{inFlight ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />} Run suite</Button>
                  </div>
                </div>
                {detail.hardening && <div className="mt-4"><HardeningLadder ladder={detail.hardening} /></div>}
                <div className="mt-4 grid gap-3 text-xs md:grid-cols-3">
                  <div className="rounded-xl border p-3"><p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Rubric</p><p className="mt-1">{detail.rubric.criteria.length ? detail.rubric.criteria.map((c) => criteriaNames.get(c.id) ?? c.id).join(", ") : "Deterministic checks only"}</p><p className="text-muted-foreground">pass at {detail.rubric.pass_threshold} of 5</p></div>
                  <div className="rounded-xl border p-3"><p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Gate</p><p className="mt-1">{detail.gate.min_pass_rate}% pass rate · {formatUsd(detail.gate.max_cost_per_case_usd)} per case · p95 {Math.round(detail.gate.max_p95_ms / 1000)}s</p></div>
                  <div className="rounded-xl border p-3"><p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Cases</p><p className="mt-1">{detail.case_count} golden cases</p><p className="text-muted-foreground">{detail.cases.filter((c) => c.from_run_id).length} promoted from real runs</p></div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
                <div className="rounded-2xl border bg-card p-4">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Runs</p>
                  <ul className="mt-2 space-y-1.5" data-testid="eval-runs">
                    {runs.map((r) => (
                      <li key={r.id}>
                        <button type="button" onClick={() => openRun(r.id)} className={cn("flex w-full items-center gap-2 rounded-lg border px-2 py-1.5 text-left text-xs", active?.id === r.id && "border-brand-violet/60")} aria-label={`Open evaluation run ${r.id}`}>
                          <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", r.kind === "canary" ? "bg-brand-pink/15 text-pink-700 dark:text-pink-300" : "bg-secondary")}>{r.kind}</span>
                          <span className="flex-1 truncate">{new Date(r.created_at).toLocaleString()}</span>
                          {r.status === "completed" ? <span className={cn("font-mono", r.summary.gate_passed ? "text-brand-emerald" : "text-brand-rose")}>{r.summary.pass_rate}%</span> : <span className="text-muted-foreground">{r.status}</span>}
                          {r.drift && <span className={cn("text-[10px]", r.drift.verdict === "drift" ? "text-brand-rose" : "text-muted-foreground")}>{r.drift.verdict}</span>}
                        </button>
                      </li>
                    ))}
                    {runs.length === 0 && <li className="text-xs text-muted-foreground">Not run yet.</li>}
                  </ul>
                </div>
                <div className="rounded-2xl border bg-card p-4" data-testid="eval-result">
                  {!active ? <p className="text-xs text-muted-foreground">Run the suite to see per-case results.</p> : (
                    <>
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        {active.status === "completed" ? (
                          <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-medium", active.summary.gate_passed ? "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300" : "bg-brand-rose/15 text-rose-700 dark:text-rose-300")} data-testid="gate-verdict">{active.summary.gate_passed ? <CheckCircle2 className="size-3.5" /> : <XCircle className="size-3.5" />} Gate {active.summary.gate_passed ? "cleared" : "not cleared"}</span>
                        ) : <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-1.5 py-0.5"><Loader2 className="size-3.5 animate-spin" /> {active.status} · {active.results?.length ?? 0} of {detail.case_count} cases</span>}
                        {active.status === "completed" && <span className="font-mono text-muted-foreground">{active.summary.passed}/{active.summary.cases} passed · {active.summary.pass_rate}% · avg score {active.summary.avg_score ?? "n/a"} · {formatUsd(active.summary.cost_usd ?? 0)} · p95 {active.summary.p95_ms} ms</span>}
                        {active.drift && <span className={cn("rounded-md px-1.5 py-0.5 text-[11px]", active.drift.verdict === "drift" ? "bg-brand-rose/15 text-rose-700 dark:text-rose-300" : "bg-secondary")}>{active.drift.verdict === "drift" ? `Drift: ${active.drift.reasons.join("; ")}` : "Stable against baseline"}{active.drift.actions?.length ? ` · ${active.drift.actions.join(", ")}` : ""}</span>}
                      </div>
                      <ol className="mt-3 space-y-2" data-testid="case-results">
                        {(active.results ?? []).map((r) => (
                          <li key={r.case_id} className="rounded-xl border p-2.5 text-xs">
                            <div className="flex items-center gap-2">
                              {r.passed ? <CheckCircle2 className="size-3.5 text-brand-emerald" /> : <XCircle className="size-3.5 text-brand-rose" />}
                              <span className="font-medium">{r.name || r.case_id}</span>
                              <span className="ml-auto font-mono text-muted-foreground">{r.avg_score !== null ? `score ${r.avg_score}` : ""} · {formatUsd(r.cost_usd)} · {r.ms} ms</span>
                              {r.run_id && <a href={`/operate/runs/${r.run_id}`} className="text-brand-violet-soft hover:underline">run</a>}
                            </div>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {r.checks.map((c) => <span key={c.check} title={c.detail} className={cn("rounded px-1.5 py-0.5 font-mono text-[10px]", c.passed ? "bg-brand-emerald/10 text-emerald-700 dark:text-emerald-300" : "bg-brand-rose/10 text-rose-700 dark:text-rose-300")}>{c.check}</span>)}
                              {r.scores.map((s) => <span key={s.criterion} title={s.rationale} className="rounded bg-brand-cyan/10 px-1.5 py-0.5 font-mono text-[10px] text-cyan-700 dark:text-cyan-300">{criteriaNames.get(s.criterion) ?? s.criterion}: {s.score ?? "n/a"}</span>)}
                            </div>
                            {r.error && <p className="mt-1 text-brand-rose">{r.error}</p>}
                          </li>
                        ))}
                      </ol>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </section>
      </div>

      <SuiteBuilder open={building} onOpenChange={setBuilding} agents={agents} recentRuns={recentRuns} library={library} onCreated={(s) => { setSuites((list) => [s, ...list]); select(s); }} />
    </div>
  );
}
