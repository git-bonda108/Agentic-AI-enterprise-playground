"use client";

import { Bot, CheckCircle2, Cpu, Loader2, ShieldCheck, UserCheck } from "lucide-react";
import type { BlueprintManifest, RunRecord } from "@/lib/playground-types";
import { formatTokens, formatUsd } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type Lane = { key: string; title: string; caption: string; kinds: string[]; accent: string; icon: React.ComponentType<{ className?: string }> };

const LANES: Lane[] = [
  { key: "deterministic", title: "Deterministic", caption: "read-only · no model", kinds: ["tool", "deterministic"], accent: "text-brand-cyan", icon: Cpu },
  { key: "agentic", title: "Agentic", caption: "governed models · metered", kinds: ["llm"], accent: "text-brand-violet-soft", icon: Bot },
  { key: "governed", title: "Governed", caption: "gates · human decisions", kinds: ["gate", "human"], accent: "text-brand-pink", icon: ShieldCheck },
];

function stageState(nodeId: string, run: RunRecord): "done" | "active" | "pending" {
  if (run.steps.some((s) => s.node === nodeId)) return "done";
  const live = run.status === "running" || run.status === "waiting_review";
  return live ? "active" : "pending";
}

function tableFrom(output: Record<string, unknown> | null): { title: string; rows: Record<string, unknown>[]; columns: string[] } | null {
  if (!output) return null;
  const preferred = ["escalated", "anomalies", "results", "blockers", "retrieved", "sources", "invalid_citations", "recommendations", "table"];
  for (const key of [...preferred, ...Object.keys(output)]) {
    const v = output[key];
    if (Array.isArray(v) && v.length > 0 && typeof v[0] === "object" && v[0] !== null) {
      const rows = v as Record<string, unknown>[];
      const columns = Object.keys(rows[0]).filter((c) => typeof rows[0][c] !== "object" || rows[0][c] === null || Array.isArray(rows[0][c])).slice(0, 5);
      return { title: key.replace(/_/g, " "), rows: rows.slice(0, 8), columns };
    }
  }
  return null;
}

/** The same run as a control room: three governed lanes, the record under review, the live reasoning feed, the exception ledger and the outcome. */
export function ControlRoom({ run, manifest }: { run: RunRecord; manifest: BlueprintManifest }) {
  const nodes = manifest.graph.nodes;
  const byLane = LANES.map((lane) => ({ lane, nodes: nodes.filter((n) => lane.kinds.includes(n.kind)) })).filter((l) => l.nodes.length > 0);
  const out = run.output ?? null;
  const ledger = tableFrom(out);
  const humanSteps = run.steps.filter((s) => s.kind === "human").length;
  const modelSteps = run.steps.filter((s) => s.kind === "llm").length;
  const headline = (out?.summary_md ?? out?.answer_md ?? out?.path_md ?? out?.digest_md ?? out?.narrative_md) as string | undefined;
  const results = Array.isArray(out?.results) ? (out!.results as unknown[]) : null;
  const escalated = Array.isArray(out?.escalated) ? (out!.escalated as unknown[]) : null;
  const cleared = results && escalated ? results.length - escalated.length : null;
  const tiles = [
    { label: "Steps", value: String(run.steps.length) },
    { label: "Model calls", value: String(modelSteps) },
    { label: "Human gates", value: String(humanSteps) },
    { label: "Cost", value: formatUsd(run.cost_usd) },
    { label: "Tokens", value: formatTokens(run.tokens_in + run.tokens_out) },
  ];
  const inputEntries = Object.entries(run.input ?? {}).slice(0, 8);

  return (
    <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]" data-testid="control-room">
      <div className="space-y-4">
        <section className="rounded-2xl border bg-card p-4" aria-label="Governed pipeline">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Governed pipeline · one record end to end</p>
          <div className="mt-3 space-y-3">
            {byLane.map(({ lane, nodes: laneNodes }) => (
              <div key={lane.key} className="rounded-xl border p-3">
                <p className={cn("flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em]", lane.accent)}><lane.icon className="size-3.5" /> {lane.title} <span className="font-normal normal-case tracking-normal text-muted-foreground">· {lane.caption}</span></p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  {laneNodes.map((n) => {
                    const state = stageState(n.id, run);
                    const step = run.steps.find((s) => s.node === n.id);
                    return (
                      <div key={n.id} className={cn("rounded-lg border p-2.5", state === "done" && "border-brand-emerald/40", state === "active" && "beam-border border-brand-violet/60")} data-testid={`stage-${n.id}`}>
                        <p className="flex items-center gap-1.5 text-sm font-semibold">{state === "done" ? <CheckCircle2 className="size-3.5 text-brand-emerald" /> : state === "active" ? <Loader2 className="size-3.5 animate-spin text-brand-violet-soft" /> : <span className="size-3.5 rounded-full border" />}{n.label}</p>
                        <p className="mt-0.5 line-clamp-2 font-mono text-[10.5px] text-muted-foreground">{step ? `${step.summary}${step.ms ? ` · ${step.ms} ms` : ""}` : manifest.tiers[n.id] ?? n.kind}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border bg-card p-4" aria-label="Exception ledger">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Exception ledger · audit trail{ledger ? ` · ${ledger.title}` : ""}</p>
          {ledger ? (
            <table className="mt-2 w-full text-xs" data-testid="ledger-table">
              <thead className="text-left text-[10px] uppercase tracking-wider text-muted-foreground"><tr>{ledger.columns.map((c) => <th key={c} className="py-1 pr-2">{c.replace(/_/g, " ")}</th>)}</tr></thead>
              <tbody>{ledger.rows.map((r, i) => <tr key={i} className="border-t">{ledger.columns.map((c) => <td key={c} className="py-1.5 pr-2 font-mono">{Array.isArray(r[c]) ? (r[c] as unknown[]).map(String).join(", ") : String(r[c] ?? "")}</td>)}</tr>)}</tbody>
            </table>
          ) : <p className="mt-2 text-xs text-muted-foreground">{run.status === "completed" ? "No exceptions recorded for this run." : "The ledger fills in as the run produces records."}</p>}
        </section>
      </div>

      <div className="space-y-4">
        <section className="rounded-2xl border bg-card p-4" aria-label="Record under review">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Record under review</p>
          <p className="mt-1 text-lg font-semibold">{manifest.name}</p>
          <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
            {inputEntries.map(([k, v]) => <div key={k} className={cn("rounded-lg border px-2 py-1.5", (v === "" || v === null) && "border-brand-rose/50")}><dt className="font-mono text-[10px] text-muted-foreground">{k}</dt><dd className="truncate font-mono">{v === "" || v === null ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v)}</dd></div>)}
            {inputEntries.length === 0 && <p className="col-span-2 text-muted-foreground">No input fields.</p>}
          </dl>
        </section>

        <section className="rounded-2xl border bg-card p-4" aria-label="Agent reasoning">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Agent reasoning · {run.status === "running" ? "live" : "trace"}</p>
          <ol className="mt-2 max-h-72 space-y-1.5 overflow-auto text-xs" data-testid="reasoning-feed">
            {run.steps.map((s, i) => (
              <li key={`${s.node}-${i}`} className="flex gap-2">
                <span className={cn("mt-1 size-1.5 shrink-0 rounded-full", s.kind === "llm" ? "bg-brand-violet" : s.kind === "human" ? "bg-brand-pink" : s.kind === "gate" ? "bg-brand-amber" : "bg-brand-cyan")} />
                <span><span className="font-mono text-[10px] text-muted-foreground">{s.node}</span> {s.summary}</span>
              </li>
            ))}
            {run.steps.length === 0 && <li className="text-muted-foreground">Waiting for the first step…</li>}
          </ol>
        </section>

        <section className="rounded-2xl border bg-card p-4" aria-label="Outcome">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Outcome</p>
          <div className="mt-2 rounded-xl border border-brand-emerald/40 bg-brand-emerald/10 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-700 dark:text-emerald-300">{run.status === "completed" ? "Completed under governance" : run.status === "waiting_review" ? "Waiting for a person" : run.status}</p>
            <p className="mt-1 font-mono text-2xl font-semibold text-emerald-700 dark:text-emerald-300">{cleared !== null ? cleared : formatUsd(run.cost_usd)}</p>
            <p className="text-[11px] text-muted-foreground">{cleared !== null ? `records cleared automatically · ${escalated!.length} sent to a person` : "metered cost of this run"}</p>
          </div>
          <div className="mt-2 grid grid-cols-5 gap-1.5">
            {tiles.map((t) => <div key={t.label} className="rounded-lg border p-2 text-center"><p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">{t.label}</p><p className="mt-0.5 font-mono text-sm font-semibold">{t.value}</p></div>)}
          </div>
          {headline && <p className="mt-2 line-clamp-4 text-xs text-muted-foreground">{headline.replace(/[#*_`>]/g, "").slice(0, 400)}</p>}
          <p className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground"><UserCheck className="size-3" /> Deterministic steps find and match · models reason over exceptions · every write waits for a person.</p>
        </section>
      </div>
    </div>
  );
}
