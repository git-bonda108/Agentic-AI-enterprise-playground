"use client";

import { useState } from "react";
import { ArrowLeft, ArrowRight, Check, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { EvalCase, EvalLibrary, EvalSuiteRecord, RunRecord } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type AgentOption = { id: string; name: string; samples: { name: string; input: Record<string, unknown> }[] };
const STEPS = ["Agent", "Cases", "Rubric", "Gate", "Canary"];

/** Five guided steps, each explaining what it does and why, ending with a runnable suite and an optional nightly canary. */
export function SuiteBuilder({ open, onOpenChange, agents, recentRuns, library, onCreated }: { open: boolean; onOpenChange: (o: boolean) => void; agents: AgentOption[]; recentRuns: RunRecord[]; library: EvalLibrary; onCreated: (s: EvalSuiteRecord) => void }) {
  const [step, setStep] = useState(0);
  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const [name, setName] = useState("");
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [criteria, setCriteria] = useState<string[]>(["correctness"]);
  const [threshold, setThreshold] = useState(3);
  const [gate, setGate] = useState({ ...library.default_gate });
  const [canary, setCanary] = useState({ enabled: false, hour_utc: 2, auto_rollback: true });
  const [draft, setDraft] = useState({ input: "", contains: "" });
  const [saving, setSaving] = useState(false);

  const agent = agents.find((a) => a.id === agentId);
  const runsForAgent = recentRuns.filter((r) => r.blueprint_id === agentId && r.status === "completed").slice(0, 6);
  // plain text goes into the agent's primary input field, learned from its samples (question, task, …)
  const primaryKey = Object.keys(agent?.samples?.[0]?.input ?? {})[0] ?? "task";

  const addFromSample = (s: { name: string; input: Record<string, unknown> }) => setCases((c) => [...c, { id: `s${c.length + 1}`, name: s.name, input: s.input, expect: { status: "completed" } }]);
  const addFromRun = (r: RunRecord) => {
    const out = r.output ?? {};
    const expect: Record<string, unknown> = { status: "completed", output_has: Object.keys(out).filter((k) => !k.endsWith("_md")).slice(0, 8) };
    if (Array.isArray(out.citations) && out.citations.length) expect.cites = true;
    setCases((c) => [...c, { id: `r${r.id.slice(0, 8)}`, name: String(Object.values(r.input)[0] ?? r.id).slice(0, 60), input: r.input, expect, from_run_id: r.id }]);
  };
  const addManual = () => {
    if (!draft.input.trim()) return;
    let input: Record<string, unknown>;
    try { input = draft.input.trim().startsWith("{") ? JSON.parse(draft.input) : { [primaryKey]: draft.input.trim() }; } catch { toast.error("Input must be plain text or valid JSON"); return; }
    const expect: Record<string, unknown> = { status: "completed" };
    if (draft.contains.trim()) expect.contains = draft.contains.trim();
    setCases((c) => [...c, { id: `m${c.length + 1}`, name: draft.input.slice(0, 60), input, expect }]);
    setDraft({ input: "", contains: "" });
  };

  const create = async () => {
    if (name.trim().length < 2) { toast.error("Name the suite"); return; }
    if (cases.length === 0) { toast.error("Add at least one case"); return; }
    setSaving(true);
    const res = await fetch("/api/pg/v1/evals/suites", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ blueprint_id: agentId, name, description: `Built in the guided wizard for ${agent?.name ?? agentId}`, cases, rubric: { criteria: criteria.map((id) => ({ id, weight: 1 })), pass_threshold: threshold }, gate }) });
    if (!res.ok) { setSaving(false); toast.error("Could not create the suite"); return; }
    const suite = (await res.json()) as EvalSuiteRecord;
    if (canary.enabled) {
      await fetch(`/api/pg/v1/evals/suites/${suite.id}/canary`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ enabled: true, hour_utc: canary.hour_utc, auto_rollback: canary.auto_rollback }) });
    }
    setSaving(false);
    onCreated(suite);
    onOpenChange(false);
    setStep(0); setCases([]); setName("");
    toast.success(`${suite.name} is ready to run`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Build an evaluation suite</DialogTitle>
          <DialogDescription>Five short steps. Each one says what it adds and why it matters, so the suite you end with is one you can defend.</DialogDescription>
        </DialogHeader>
        <ol className="flex flex-wrap gap-1 text-xs" aria-label="Steps">
          {STEPS.map((s, i) => <li key={s} className={cn("rounded-lg border px-2.5 py-1", i === step ? "border-brand-violet/60 bg-secondary" : i < step ? "text-brand-emerald" : "text-muted-foreground")}>{i < step ? <Check className="mr-1 inline size-3" /> : `${i + 1}. `}{s}</li>)}
        </ol>

        {step === 0 && (
          <div className="grid gap-3 text-xs">
            <p className="text-muted-foreground"><strong className="text-foreground">What this does.</strong> Picks the agent under test and names the suite. Every case will run this agent for real, metered to you.</p>
            <label>Agent<select value={agentId} onChange={(e) => { setAgentId(e.target.value); setCases([]); }} aria-label="Agent under test" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm">{agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
            <label>Suite name<input value={name} onChange={(e) => setName(e.target.value)} aria-label="Suite name" placeholder={`${agent?.name ?? "Agent"} regression set`} className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
          </div>
        )}

        {step === 1 && (
          <div className="grid gap-3 text-xs">
            <p className="text-muted-foreground"><strong className="text-foreground">What this does.</strong> Golden cases are inputs with expectations. Start from the agent&apos;s samples, promote a real run you liked, or write your own with a phrase the answer must contain.</p>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border p-3">
                <p className="font-semibold">From samples</p>
                {(agent?.samples ?? []).map((s) => <button key={s.name} type="button" onClick={() => addFromSample(s)} className="mt-1 block w-full truncate rounded-lg border px-2 py-1 text-left hover:border-brand-violet/40" aria-label={`Add sample ${s.name}`}><Plus className="mr-1 inline size-3" />{s.name}</button>)}
                {(agent?.samples ?? []).length === 0 && <p className="mt-1 text-muted-foreground">No samples for this agent.</p>}
              </div>
              <div className="rounded-xl border p-3">
                <p className="font-semibold">From recent runs</p>
                {runsForAgent.map((r) => <button key={r.id} type="button" onClick={() => addFromRun(r)} className="mt-1 block w-full truncate rounded-lg border px-2 py-1 text-left hover:border-brand-violet/40" aria-label={`Add run ${r.id}`}><Plus className="mr-1 inline size-3" />{String(Object.values(r.input)[0] ?? r.id).slice(0, 40)}</button>)}
                {runsForAgent.length === 0 && <p className="mt-1 text-muted-foreground">Run the agent once and it appears here.</p>}
              </div>
              <div className="rounded-xl border p-3">
                <p className="font-semibold">Write one</p>
                <textarea value={draft.input} onChange={(e) => setDraft({ ...draft, input: e.target.value })} rows={2} aria-label="Case input" placeholder={`${primaryKey} text, or JSON input`} className="mt-1 w-full rounded-lg border bg-background p-2" />
                <input value={draft.contains} onChange={(e) => setDraft({ ...draft, contains: e.target.value })} aria-label="Answer must contain" placeholder="Answer must contain (optional)" className="mt-1 h-8 w-full rounded-lg border bg-background px-2" />
                <Button size="sm" variant="outline" className="mt-2" onClick={addManual} aria-label="Add written case"><Plus className="size-3.5" /> Add case</Button>
              </div>
            </div>
            <ul className="divide-y rounded-xl border" data-testid="builder-cases">
              {cases.map((c, i) => (
                <li key={c.id} className="flex items-center justify-between gap-2 px-3 py-1.5">
                  <span className="truncate"><span className="font-mono text-muted-foreground">{c.id}</span> {c.name} <span className="text-muted-foreground">· expects {Object.keys(c.expect).join(", ")}</span></span>
                  <button type="button" onClick={() => setCases((list) => list.filter((_, j) => j !== i))} aria-label={`Remove case ${c.id}`} className="rounded p-1 hover:bg-muted hover:text-destructive"><Trash2 className="size-3.5" /></button>
                </li>
              ))}
              {cases.length === 0 && <li className="px-3 py-2 text-muted-foreground">No cases yet.</li>}
            </ul>
          </div>
        )}

        {step === 2 && (
          <div className="grid gap-3 text-xs">
            <p className="text-muted-foreground"><strong className="text-foreground">What this does.</strong> Deterministic checks catch structure; a rubric catches quality. An Economy-tier model scores each criterion from 1 to 5, and a case passes only if the average clears the threshold. Judging is metered like any other call.</p>
            <div className="grid gap-2 sm:grid-cols-2" data-testid="rubric-picker">
              {library.rubric.map((c) => (
                <label key={c.id} className={cn("flex cursor-pointer gap-2 rounded-xl border p-2.5", criteria.includes(c.id) && "border-brand-violet/60 bg-brand-violet/5")}>
                  <input type="checkbox" className="mt-0.5 accent-[var(--brand-violet)]" checked={criteria.includes(c.id)} onChange={(e) => setCriteria((cur) => (e.target.checked ? [...cur, c.id] : cur.filter((x) => x !== c.id)))} aria-label={`Criterion ${c.name}`} />
                  <span><span className="font-semibold">{c.name}</span><span className="block text-muted-foreground">{c.description}</span><span className="block text-[11px] text-brand-violet-soft">Why: {c.why}</span></span>
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2">Pass threshold (average score out of 5)<input type="number" min={1} max={5} step={0.5} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} aria-label="Pass threshold" className="h-8 w-20 rounded-lg border bg-background px-2" /></label>
          </div>
        )}

        {step === 3 && (
          <div className="grid gap-3 text-xs">
            <p className="text-muted-foreground"><strong className="text-foreground">What this does.</strong> The gate is the promise a run must keep before the agent can move up the hardening ladder: enough cases pass, at a cost and latency you can afford.</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <label>Minimum pass rate (%)<input type="number" min={0} max={100} value={gate.min_pass_rate} onChange={(e) => setGate({ ...gate, min_pass_rate: Number(e.target.value) })} aria-label="Minimum pass rate" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
              <label>Max cost per case (USD)<input type="number" min={0} step={0.01} value={gate.max_cost_per_case_usd} onChange={(e) => setGate({ ...gate, max_cost_per_case_usd: Number(e.target.value) })} aria-label="Max cost per case" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
              <label>Max p95 latency (ms)<input type="number" min={0} step={1000} value={gate.max_p95_ms} onChange={(e) => setGate({ ...gate, max_p95_ms: Number(e.target.value) })} aria-label="Max p95 latency" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="grid gap-3 text-xs">
            <p className="text-muted-foreground"><strong className="text-foreground">What this does.</strong> A canary reruns the suite every night, compares with the last good run and raises an alert on drift. With automatic rollback, a wizard agent returns to its last good version on its own; built-in blueprints are demoted a level instead.</p>
            <label className="flex items-center gap-2"><input type="checkbox" checked={canary.enabled} onChange={(e) => setCanary({ ...canary, enabled: e.target.checked })} className="accent-[var(--brand-violet)]" aria-label="Enable nightly canary" /> Enable the nightly canary</label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label>Run at (hour, UTC)<input type="number" min={0} max={23} value={canary.hour_utc} onChange={(e) => setCanary({ ...canary, hour_utc: Number(e.target.value) })} aria-label="Canary hour" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
              <label className="flex items-center gap-2 self-end"><input type="checkbox" checked={canary.auto_rollback} onChange={(e) => setCanary({ ...canary, auto_rollback: e.target.checked })} className="accent-[var(--brand-violet)]" aria-label="Automatic rollback" /> Roll back automatically on drift</label>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <Button variant="outline" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0} aria-label="Previous step"><ArrowLeft className="size-3.5" /> Back</Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={() => setStep((s) => s + 1)} disabled={(step === 0 && (!agentId || name.trim().length < 2)) || (step === 1 && cases.length === 0)} aria-label="Next step">Next <ArrowRight className="size-3.5" /></Button>
          ) : (
            <Button className="glow-violet" onClick={create} disabled={saving} aria-label="Create suite">{saving ? "Creating…" : "Create suite"}</Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
