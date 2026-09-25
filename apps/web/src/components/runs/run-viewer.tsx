"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, Clock, Loader2, NotebookPen, RotateCcw, UserCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { GraphBeams } from "@/components/runs/graph-beams";
import { Markdown } from "@/components/playground/markdown";
import { formatTokens, formatUsd, type BlueprintManifest, type RunRecord } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const STATUS: Record<RunRecord["status"], { label: string; cls: string; icon: React.ComponentType<{ className?: string }> }> = {
  queued: { label: "Queued", cls: "bg-muted text-muted-foreground", icon: Clock },
  running: { label: "Running", cls: "bg-brand-cyan/15 text-cyan-700 dark:text-cyan-300", icon: Loader2 },
  waiting_review: { label: "Waiting for review", cls: "bg-brand-pink/15 text-pink-700 dark:text-pink-300", icon: UserCheck },
  completed: { label: "Completed", cls: "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300", icon: CheckCircle2 },
  failed: { label: "Failed", cls: "bg-brand-rose/15 text-rose-700 dark:text-rose-300", icon: AlertTriangle },
};

export function RunStatusPill({ status, testId }: { status: RunRecord["status"]; testId?: string }) {
  const s = STATUS[status];
  return <span data-testid={testId} className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium", s.cls)}><s.icon className={cn("size-3", status === "running" && "animate-spin")} /> {s.label}</span>;
}

export function RunViewer({ initial, manifest }: { initial: RunRecord; manifest: BlueprintManifest }) {
  const [run, setRun] = useState(initial);
  const [choice, setChoice] = useState<string>(initial.review?.options?.[0] ?? "");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const live = run.status === "queued" || run.status === "running";
  const [pendingResume, setPendingResume] = useState(false);
  const polling = live || pendingResume;

  useEffect(() => {
    if (!polling) return;
    const t = setInterval(async () => {
      const res = await fetch(`/api/pg/v1/runs/${run.id}`);
      if (res.ok) {
        const next = (await res.json()) as RunRecord;
        setRun(next);
        if (next.status !== "waiting_review") setPendingResume(false);
        if (next.review?.options?.length) setChoice((c) => c || next.review!.options![0]);
      }
    }, 1000);
    return () => clearInterval(t);
  }, [polling, run.id]);

  const resume = async () => {
    setSubmitting(true);
    const answer = run.review?.free_text ? { decision: choice, notes } : choice;
    const res = await fetch(`/api/pg/v1/runs/${run.id}/resume`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ answer }) });
    setSubmitting(false);
    if (!res.ok) { toast.error("Could not resume the run"); return; }
    setRun((await res.json()) as RunRecord);
    setPendingResume(true);
    setChoice("");
    toast.success("Decision recorded, the run continues");
  };

  const duration = ((new Date(run.finished_at ?? run.updated_at).getTime() - new Date(run.created_at).getTime()) / 1000).toFixed(1);
  const out = run.output ?? {};
  const md = (out.summary_md ?? out.answer_md ?? out.path_md ?? out.revised_md ?? out.narrative_md) as string | undefined;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground"><Link href="/operate/runs" className="hover:text-foreground">Runs</Link> · {manifest.family}</p>
          <h1 className="text-2xl font-semibold tracking-tight">{manifest.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{manifest.pattern}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <RunStatusPill status={run.status} testId="run-status" />
          <span className="rounded-md border bg-card px-2 py-1 font-mono" data-testid="run-cost">{formatUsd(run.cost_usd)}</span>
          <span className="rounded-md border bg-card px-2 py-1 font-mono">{formatTokens(run.tokens_in)} in · {formatTokens(run.tokens_out)} out</span>
          <span className="rounded-md border bg-card px-2 py-1 font-mono">{duration}s</span>
          <Link href={`/build/agents?blueprint=${manifest.id}`} className="inline-flex h-7 items-center gap-1 rounded-md border bg-card px-2 hover:border-brand-violet/40"><RotateCcw className="size-3" /> Run again</Link>
          <Link href={`/build/notebooks?run=${run.id}`} className="inline-flex h-7 items-center gap-1 rounded-md border bg-card px-2 hover:border-brand-violet/40"><NotebookPen className="size-3" /> Open in notebook</Link>
        </div>
      </div>

      <section className="rounded-2xl border bg-card p-4" aria-label="Run graph">
        <GraphBeams manifest={manifest} run={run} />
      </section>

      {run.status === "waiting_review" && run.review && (
        <section className="beam-border relative rounded-2xl border bg-card p-5" aria-label="Human review" data-testid="review-panel">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brand-pink"><UserCheck className="size-4" /> Your decision is needed</p>
          <p className="mt-2 text-base font-medium">{run.review.question}</p>
          {run.review.context && <p className="mt-1 text-sm text-muted-foreground">Context: {run.review.context}</p>}
          {run.review.items && run.review.items.length > 0 && (
            <ul className="mt-3 divide-y rounded-xl border text-sm">
              {run.review.items.map((it) => <li key={it.label} className="px-3 py-2"><span className="font-medium">{it.label}</span><span className="block text-xs text-muted-foreground">{it.detail}</span></li>)}
            </ul>
          )}
          <div className="mt-4 flex flex-wrap gap-2" role="radiogroup" aria-label="Decision">
            {(run.review.options ?? []).map((o) => (
              <button key={o} type="button" role="radio" aria-checked={choice === o} onClick={() => setChoice(o)} className={cn("h-9 rounded-lg border px-3 text-sm", choice === o ? "border-brand-violet/70 bg-secondary text-secondary-foreground" : "bg-card hover:border-brand-violet/40")}>{o.replace(/_/g, " ")}</button>
            ))}
          </div>
          {run.review.free_text && (
            <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={run.review.free_text} aria-label={run.review.free_text} className="mt-3 h-9 w-full rounded-lg border bg-background px-3 text-sm outline-none focus-visible:border-brand-violet/60" />
          )}
          <Button className="mt-4 glow-violet" onClick={resume} disabled={!choice || submitting} aria-label="Submit decision">{submitting ? "Submitting…" : "Submit decision"}</Button>
        </section>
      )}

      {run.status === "failed" && run.error && (
        <section role="alert" className="rounded-2xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">{run.error}</section>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
        <section className="rounded-2xl border bg-card" aria-label="Steps">
          <h2 className="border-b px-4 py-2.5 text-sm font-semibold">Steps</h2>
          <ol className="divide-y" data-testid="run-steps">
            {run.steps.length === 0 && <li className="px-4 py-6 text-sm text-muted-foreground">Starting…</li>}
            {run.steps.map((s, i) => (
              <li key={`${s.node}-${i}`} className="px-4 py-2.5">
                <div className="flex items-center gap-2 text-xs">
                  <span className={cn("size-1.5 rounded-full", s.kind === "llm" ? "bg-brand-violet-soft" : s.kind === "human" ? "bg-brand-pink" : s.kind === "gate" ? "bg-brand-amber" : "bg-brand-cyan")} />
                  <span className="font-medium">{manifest.graph.nodes.find((n) => n.id === s.node)?.label ?? s.node}</span>
                  <span className="ml-auto font-mono text-[10px] text-muted-foreground">{new Date(s.at).toLocaleTimeString()}</span>
                </div>
                <p className="mt-1 text-sm">{s.summary}</p>
                {Object.keys(s.detail ?? {}).length > 0 && <pre className="mt-1 max-h-32 overflow-auto rounded-lg bg-muted p-2 font-mono text-[10.5px] text-muted-foreground">{JSON.stringify(s.detail, null, 1)}</pre>}
              </li>
            ))}
          </ol>
        </section>
        <section className="rounded-2xl border bg-card" aria-label="Output">
          <h2 className="border-b px-4 py-2.5 text-sm font-semibold">Output</h2>
          <div className="p-4" data-testid="run-output">
            {!run.output && <p className="text-sm text-muted-foreground">{live ? "The result appears here when the run finishes." : run.status === "waiting_review" ? "Waiting for your decision above." : "No output."}</p>}
            {md && <Markdown text={md} />}
            {run.output && Object.keys(out).filter((k) => !k.endsWith("_md")).length > 0 && (
              <details className="mt-3 text-xs">
                <summary className="cursor-pointer text-muted-foreground">Structured output</summary>
                <pre className="mt-2 max-h-96 overflow-auto rounded-lg bg-muted p-3 font-mono text-[11px]">{JSON.stringify(Object.fromEntries(Object.entries(out).filter(([k]) => !k.endsWith("_md"))), null, 2)}</pre>
              </details>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
