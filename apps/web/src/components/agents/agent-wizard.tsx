"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Download, Play, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { RunDialog, type RunTarget } from "@/components/agents/run-dialog";
import type { CustomAgent } from "@/lib/playground-types";

const KNOWLEDGE = [{ id: "policies", label: "Company policies" }, { id: "learning_refs", label: "Learning references" }];

/** The six Copilot Studio fields: name, description, instructions, knowledge, starter prompts, publish. */
export function AgentWizard({ initial, ownerId }: { initial: CustomAgent[]; ownerId: string }) {
  const router = useRouter();
  const [agents, setAgents] = useState(initial);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", instructions: "", knowledge: [] as string[], starters: ["", "", ""], published: true });
  const [saving, setSaving] = useState(false);
  const [runTarget, setRunTarget] = useState<RunTarget | null>(null);

  const save = async () => {
    const body = { ...form, starters: form.starters.filter((s) => s.trim()) };
    if (body.name.length < 2 || body.description.length < 5 || body.instructions.length < 20) { toast.error("Name, description and at least 20 characters of instructions are needed"); return; }
    setSaving(true);
    const res = await fetch("/api/pg/v1/custom-agents", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    setSaving(false);
    if (!res.ok) { toast.error("Could not save the agent"); return; }
    const created = (await res.json()) as CustomAgent;
    setAgents((a) => [created, ...a]);
    setOpen(false);
    setForm({ name: "", description: "", instructions: "", knowledge: [], starters: ["", "", ""], published: true });
    toast.success(`${created.name} is ready to run`);
    router.refresh();
  };
  const remove = async (a: CustomAgent) => {
    const res = await fetch(`/api/pg/v1/custom-agents/${a.id}`, { method: "DELETE" });
    if (res.ok) setAgents((list) => list.filter((x) => x.id !== a.id));
  };
  const run = (a: CustomAgent) => setRunTarget({ id: a.id, name: a.name, description: a.description, samples: (a.starters.length ? a.starters : ["Describe what you do."]).map((s) => ({ name: s.slice(0, 48), input: { task: s } })), input_schema: { task: "text", context: "optional text" }, datasets: a.knowledge });

  return (
    <section>
      <div className="mb-3 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Your agents</h2>
          <p className="text-xs text-muted-foreground">Build one with six fields, run it under your policy, export it for Copilot Studio.</p>
        </div>
        <Button className="glow-violet" onClick={() => setOpen(true)} aria-label="Create your own agent"><Sparkles className="size-4" /> Create your own agent</Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="custom-agents">
        {agents.length === 0 && <p className="col-span-full rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">No custom agents yet. The wizard takes about a minute.</p>}
        {agents.map((a) => (
          <article key={a.id} className="card-hover flex flex-col rounded-2xl border bg-card p-4" aria-label={a.name}>
            <div className="flex items-center justify-between">
              <span className="rounded-md bg-brand-emerald/15 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">{a.published ? "Published" : "Private"}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{a.knowledge.length ? `knowledge: ${a.knowledge.join(", ")}` : "no knowledge"}</span>
            </div>
            <h3 className="mt-2 text-base font-semibold">{a.name}</h3>
            <p className="mt-1 flex-1 text-sm text-muted-foreground">{a.description}</p>
            <div className="mt-3 flex items-center gap-2">
              <Button size="sm" onClick={() => run(a)} aria-label={`Run ${a.name}`}><Play className="size-3.5" /> Run</Button>
              <a href={`/api/pg/v1/custom-agents/${a.id}/export/declarative-agent`} className="inline-flex h-8 items-center gap-1 rounded-lg border px-2.5 text-xs hover:border-brand-violet/40" aria-label={`Export ${a.name} for Copilot Studio`}><Download className="size-3.5" /> Copilot Studio</a>
              {a.owner_id === ownerId && <button type="button" onClick={() => remove(a)} aria-label={`Delete ${a.name}`} className="ml-auto grid size-8 place-items-center rounded-lg hover:bg-muted hover:text-destructive"><Trash2 className="size-3.5" /></button>}
            </div>
          </article>
        ))}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create your own agent</DialogTitle>
            <DialogDescription>The same six things Copilot Studio asks for. It runs here under your model policy and budget, and exports as a declarative agent manifest.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 text-xs">
            <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} aria-label="Agent name" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" placeholder="Expense helper" /></label>
            <label>Description<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} aria-label="Agent description" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" placeholder="Answers expense questions for the finance team" /></label>
            <label>Instructions<textarea value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} rows={5} aria-label="Agent instructions" className="mt-1 w-full rounded-lg border bg-background p-2 text-sm" placeholder="You answer expense and travel questions using the policies provided and cite the policy id." /></label>
            <div>
              <p>Knowledge</p>
              <div className="mt-1 flex flex-wrap gap-2">
                {KNOWLEDGE.map((k) => (
                  <label key={k.id} className="flex items-center gap-1.5 rounded-lg border px-2 py-1"><input type="checkbox" className="accent-[var(--brand-violet)]" checked={form.knowledge.includes(k.id)} onChange={(e) => setForm({ ...form, knowledge: e.target.checked ? [...form.knowledge, k.id] : form.knowledge.filter((x) => x !== k.id) })} aria-label={k.label} /> {k.label}</label>
                ))}
              </div>
            </div>
            <div>
              <p>Starter prompts</p>
              {form.starters.map((s, i) => (
                <input key={i} value={s} onChange={(e) => setForm({ ...form, starters: form.starters.map((x, j) => (j === i ? e.target.value : x)) })} aria-label={`Starter prompt ${i + 1}`} className="mt-1 h-8 w-full rounded-lg border bg-background px-2 text-sm" placeholder={["What is the hotel limit?", "Can I claim taxi rides?", "How do I file a claim?"][i]} />
              ))}
            </div>
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.published} onChange={(e) => setForm({ ...form, published: e.target.checked })} className="accent-[var(--brand-violet)]" aria-label="Publish to the organization" /> Publish so colleagues can run it</label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button className="glow-violet" onClick={save} disabled={saving} aria-label="Save agent">{saving ? "Saving…" : "Create agent"}</Button>
          </div>
        </DialogContent>
      </Dialog>
      {runTarget && <RunDialog key={runTarget.id} target={runTarget} onClose={() => setRunTarget(null)} />}
    </section>
  );
}
