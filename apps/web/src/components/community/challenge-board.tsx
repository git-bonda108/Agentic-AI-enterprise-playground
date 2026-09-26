"use client";

import { useState } from "react";
import { Gavel, Loader2, Lock, Plus, Send, Trophy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { ChallengeRecord, RubricCriterion } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type AgentOption = { id: string; name: string; primaryKey: string };

export function ChallengeBoard({ initial, agents, rubric, userId, canRun, initialSelected }: { initial: ChallengeRecord[]; agents: AgentOption[]; rubric: RubricCriterion[]; userId: string; canRun: boolean; initialSelected: string | null }) {
  const [challenges, setChallenges] = useState(initial);
  const [selected, setSelected] = useState<string | null>(initialSelected ?? initial[0]?.id ?? null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [form, setForm] = useState({ title: "", brief: "", badge: "Challenge winner", days_open: 7, cases: "", criteria: ["correctness", "completeness"] as string[], primaryKey: "question" });
  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const [note, setNote] = useState("");

  const current = challenges.find((c) => c.id === selected) ?? null;
  const replace = (c: ChallengeRecord) => setChallenges((list) => list.map((x) => (x.id === c.id ? c : x)));

  const create = async () => {
    const lines = form.cases.split("\n").map((l) => l.trim()).filter(Boolean);
    if (form.title.length < 3 || form.brief.length < 10 || lines.length === 0) { toast.error("Title, a brief and at least one shared case are needed"); return; }
    setBusy("create");
    const cases = lines.map((line) => { const [q, must] = line.split("=>").map((s) => s.trim()); return { input: { [form.primaryKey]: q }, expect: must ? { status: "completed", contains: must } : { status: "completed" } }; });
    const res = await fetch("/api/pg/v1/community/challenges", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ title: form.title, brief: form.brief, badge: form.badge, days_open: form.days_open, cases, rubric: { criteria: form.criteria.map((id) => ({ id, weight: 1 })), pass_threshold: 3 } }) });
    setBusy(null);
    if (!res.ok) { toast.error("Could not open the challenge"); return; }
    const c = (await res.json()) as ChallengeRecord;
    setChallenges((list) => [c, ...list]);
    setSelected(c.id);
    setCreating(false);
    toast.success("Challenge is open");
  };
  const submit = async () => {
    if (!current) return;
    setBusy("submit");
    const res = await fetch(`/api/pg/v1/community/challenges/${current.id}/submit`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ agent_id: agentId, note }) });
    setBusy(null);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "Could not submit"); return; }
    replace(await res.json());
    toast.success("Submitted. Judging happens when the owner runs the rubric.");
  };
  const judge = async () => {
    if (!current) return;
    setBusy("judge");
    const res = await fetch(`/api/pg/v1/community/challenges/${current.id}/judge`, { method: "POST" });
    setBusy(null);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "Judging failed"); return; }
    const c = (await res.json()) as ChallengeRecord;
    replace(c);
    toast.success(`Judged ${c.judged_now ?? 0} submission${c.judged_now === 1 ? "" : "s"} against the rubric`);
  };
  const close = async () => {
    if (!current) return;
    setBusy("close");
    const res = await fetch(`/api/pg/v1/community/challenges/${current.id}/close`, { method: "POST" });
    setBusy(null);
    if (res.ok) { replace(await res.json()); toast.success("Closed. The winner has a new badge."); }
  };

  const rubricNames = new Map(rubric.map((r) => [r.id, r.name]));
  const owns = current ? current.owner_id === userId || canRun : false;

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Community</p>
          <h1 className="text-2xl font-semibold tracking-tight">Challenges</h1>
          <p className="mt-1 text-sm text-muted-foreground">Time-boxed builds. Everyone gets the same brief and the same cases; the evaluation engine judges every entry with the same rubric, so the standings are earned, not voted.</p>
        </div>
        {canRun && <Button className="glow-violet" onClick={() => setCreating(true)} aria-label="Open a challenge"><Plus className="size-4" /> Open a challenge</Button>}
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[300px_1fr]">
        <aside className="space-y-2" data-testid="challenge-list">
          {challenges.map((c) => (
            <button key={c.id} type="button" onClick={() => setSelected(c.id)} aria-label={`Open challenge ${c.title}`} className={cn("card-hover w-full rounded-2xl border bg-card p-3 text-left", selected === c.id && "border-brand-violet/60")}>
              <div className="flex items-center justify-between gap-2"><span className="truncate text-sm font-semibold">{c.title}</span><span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", c.status === "open" ? "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300" : "bg-muted text-muted-foreground")}>{c.status}</span></div>
              <p className="mt-0.5 text-xs text-muted-foreground">{c.submission_count} entries · {c.status === "open" && c.time_left_h !== null ? `${Math.max(0, Math.round(c.time_left_h))} h left` : "judged"} · badge: {c.badge}</p>
            </button>
          ))}
          {challenges.length === 0 && <p className="rounded-2xl border border-dashed p-5 text-center text-xs text-muted-foreground">No challenges yet.</p>}
        </aside>

        <section className="min-w-0 rounded-2xl border bg-card p-4" data-testid="challenge-detail">
          {!current ? <p className="text-sm text-muted-foreground">Select a challenge.</p> : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">{current.title}</h2>
                  <p className="text-xs text-muted-foreground">Opened by {current.owner_name} · rubric: {current.rubric.criteria.map((c) => rubricNames.get(c.id) ?? c.id).join(", ")} · {current.cases.length} shared cases</p>
                </div>
                {owns && current.status === "open" && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={judge} disabled={busy !== null} aria-label="Judge submissions">{busy === "judge" ? <Loader2 className="size-3.5 animate-spin" /> : <Gavel className="size-3.5" />} Judge</Button>
                    <Button size="sm" variant="outline" onClick={close} disabled={busy !== null} aria-label="Close challenge"><Lock className="size-3.5" /> Close</Button>
                  </div>
                )}
              </div>
              <p className="mt-3 whitespace-pre-wrap rounded-xl border bg-muted/40 p-3 text-sm">{current.brief}</p>
              <ul className="mt-2 flex flex-wrap gap-1 text-[11px]">{current.cases.map((c, i) => <li key={i} className="rounded bg-secondary px-1.5 py-0.5">{String(Object.values(c.input)[0] ?? "").slice(0, 60)}</li>)}</ul>

              {current.status === "open" && (
                <div className="mt-4 flex flex-wrap items-end gap-2 rounded-xl border p-3 text-xs" data-testid="submit-box">
                  <label className="min-w-56 flex-1">Your entry<select value={agentId} onChange={(e) => setAgentId(e.target.value)} aria-label="Agent to submit" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm">{agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
                  <label className="min-w-56 flex-1">Note<input value={note} onChange={(e) => setNote(e.target.value)} aria-label="Submission note" placeholder="What makes it good" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
                  <Button onClick={submit} disabled={busy !== null || !agentId} aria-label="Submit entry">{busy === "submit" ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />} Submit</Button>
                </div>
              )}

              <table className="mt-4 w-full text-xs" data-testid="standings">
                <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground"><tr><th className="py-1">#</th><th>Who</th><th>Agent</th><th className="text-right">Score</th><th className="text-right">Quality</th><th className="text-right">Pass rate</th><th className="text-right">Cost</th></tr></thead>
                <tbody>
                  {[...current.submissions].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).map((s) => (
                    <tr key={s.id} className={cn("border-t", s.id === current.winner_submission_id && "bg-brand-amber/10")}>
                      <td className="py-1.5">{s.id === current.winner_submission_id ? <Trophy className="size-3.5 text-brand-amber" aria-label="Winner" /> : s.rank ?? "–"}</td>
                      <td>{s.user_name} <span className="text-muted-foreground">· {s.department}</span></td>
                      <td>{s.agent_name}{s.note ? <span className="text-muted-foreground"> · {s.note}</span> : null}</td>
                      <td className="text-right font-mono">{s.score ?? "pending"}</td>
                      <td className="text-right font-mono">{s.judged?.avg_score ?? "–"}</td>
                      <td className="text-right font-mono">{s.judged?.pass_rate !== null && s.judged?.pass_rate !== undefined ? `${s.judged.pass_rate}%` : "–"}</td>
                      <td className="text-right font-mono">{s.judged?.cost_usd !== null && s.judged?.cost_usd !== undefined ? `$${s.judged.cost_usd.toFixed(4)}` : "–"}</td>
                    </tr>
                  ))}
                  {current.submissions.length === 0 && <tr><td colSpan={7} className="py-3 text-center text-muted-foreground">No entries yet.</td></tr>}
                </tbody>
              </table>
            </>
          )}
        </section>
      </div>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Open a challenge</DialogTitle>
            <DialogDescription>Shared cases are what every entry is judged on. One per line; add &quot;=&gt; phrase&quot; to require the answer to contain something.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 text-xs">
            <label>Title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} aria-label="Challenge title" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
            <label>Brief<textarea value={form.brief} onChange={(e) => setForm({ ...form, brief: e.target.value })} rows={3} aria-label="Challenge brief" className="mt-1 w-full rounded-lg border bg-background p-2 text-sm" /></label>
            <label>Input field name<input value={form.primaryKey} onChange={(e) => setForm({ ...form, primaryKey: e.target.value })} aria-label="Input field" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 font-mono text-sm" list="challenge-input-keys" />
              <datalist id="challenge-input-keys">{[...new Set(agents.map((a) => a.primaryKey))].map((k) => <option key={k} value={k} />)}</datalist>
              <span className="mt-1 block text-[11px] text-muted-foreground">The field every entry reads its case from. {[...new Set(agents.map((a) => a.primaryKey))].map((k) => `${k}: ${agents.filter((a) => a.primaryKey === k).map((a) => a.name.replace(/ \(.*\)$/, "")).slice(0, 3).join(", ")}`).join(" · ")}</span></label>
            <label>Shared cases<textarea value={form.cases} onChange={(e) => setForm({ ...form, cases: e.target.value })} rows={4} aria-label="Shared cases" placeholder={"What is the hotel limit per night? => POL-001\nWhat do I need for a purchase over 50,000 USD? => POL-002"} className="mt-1 w-full rounded-lg border bg-background p-2 font-mono text-[12px]" /></label>
            <div>
              <p>Rubric</p>
              <div className="mt-1 flex flex-wrap gap-2">{rubric.map((r) => <label key={r.id} className="flex items-center gap-1.5 rounded-lg border px-2 py-1"><input type="checkbox" className="accent-[var(--brand-violet)]" checked={form.criteria.includes(r.id)} onChange={(e) => setForm({ ...form, criteria: e.target.checked ? [...form.criteria, r.id] : form.criteria.filter((x) => x !== r.id) })} aria-label={`Rubric ${r.name}`} /> {r.name}</label>)}</div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label>Badge for the winner<input value={form.badge} onChange={(e) => setForm({ ...form, badge: e.target.value })} aria-label="Badge" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
              <label>Days open<input type="number" min={1} max={90} value={form.days_open} onChange={(e) => setForm({ ...form, days_open: Number(e.target.value) })} aria-label="Days open" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
            </div>
          </div>
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setCreating(false)}>Cancel</Button><Button className="glow-violet" onClick={create} disabled={busy === "create"} aria-label="Create challenge">Open it</Button></div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
