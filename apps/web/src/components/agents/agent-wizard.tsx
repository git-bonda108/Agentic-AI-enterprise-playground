"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Download, Play, Plug, Search, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { RunDialog, type RunTarget } from "@/components/agents/run-dialog";
import type { CustomAgent } from "@/lib/playground-types";

const KNOWLEDGE = [{ id: "policies", label: "Company policies" }, { id: "learning_refs", label: "Learning references" }];
type Option = { id: string; name: string; hint?: string };
const EMPTY_FORM = { name: "", description: "", instructions: "", knowledge: [] as string[], skills: [] as string[], tools: [] as string[], starters: ["", "", ""], published: true };

/** The six Copilot Studio fields plus skills and connectors: name, description, instructions, knowledge, skills, tools, starter prompts, publish. */
export function AgentWizard({ initial, ownerId, skills = [], connectors = [], spaces = [], presetSkill }: { initial: CustomAgent[]; ownerId: string; skills?: Option[]; connectors?: Option[]; spaces?: Option[]; presetSkill?: string }) {
  const router = useRouter();
  const [agents, setAgents] = useState(initial);
  const [open, setOpen] = useState(Boolean(presetSkill));
  const [form, setForm] = useState({ ...EMPTY_FORM, skills: presetSkill ? [presetSkill] : [] });
  const [skillQuery, setSkillQuery] = useState("");
  const toggle = (key: "knowledge" | "skills" | "tools", id: string, on: boolean) => setForm((f) => ({ ...f, [key]: on ? [...f[key], id] : f[key].filter((x) => x !== id) }));
  const knownSkills = presetSkill && !skills.some((s) => s.id === presetSkill) ? [{ id: presetSkill, name: presetSkill }, ...skills] : skills;
  // selected skills always show first, then the best matches for the search box
  const selectedSkills = knownSkills.filter((s) => form.skills.includes(s.id));
  const matchingSkills = knownSkills.filter((s) => !form.skills.includes(s.id) && (!skillQuery || `${s.name} ${s.hint ?? ""}`.toLowerCase().includes(skillQuery.toLowerCase())));
  const shownSkills = [...selectedSkills, ...matchingSkills].slice(0, Math.max(14, selectedSkills.length));
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
    setForm(EMPTY_FORM);
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
              <span className="font-mono text-[10px] text-muted-foreground">{[a.knowledge.length ? `${a.knowledge.length} knowledge` : "", a.skills?.length ? `${a.skills.length} skills` : "", a.tools?.length ? `${a.tools.length} tools` : ""].filter(Boolean).join(" · ") || "instructions only"}</span>
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
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
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
                  <label key={k.id} className="flex items-center gap-1.5 rounded-lg border px-2 py-1"><input type="checkbox" className="accent-[var(--brand-violet)]" checked={form.knowledge.includes(k.id)} onChange={(e) => toggle("knowledge", k.id, e.target.checked)} aria-label={k.label} /> {k.label}</label>
                ))}
                {spaces.map((s) => (
                  <label key={s.id} className="flex items-center gap-1.5 rounded-lg border border-brand-violet/40 px-2 py-1"><input type="checkbox" className="accent-[var(--brand-violet)]" checked={form.knowledge.includes(`space:${s.id}`)} onChange={(e) => toggle("knowledge", `space:${s.id}`, e.target.checked)} aria-label={`Knowledge Space ${s.name}`} /> {s.name}</label>
                ))}
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between"><p>Skills <span className="text-muted-foreground">({form.skills.length} attached)</span></p>
                <label className="relative"><Search className="pointer-events-none absolute left-2 top-1.5 size-3 text-muted-foreground" /><input value={skillQuery} onChange={(e) => setSkillQuery(e.target.value)} aria-label="Search skills to attach" placeholder="Search skills" className="h-7 w-44 rounded-lg border bg-background pl-6 pr-2 text-xs" /></label>
              </div>
              <div className="mt-1 flex flex-wrap gap-2" data-testid="skill-picker">
                {shownSkills.map((s) => (
                  <label key={s.id} className="flex items-center gap-1.5 rounded-lg border px-2 py-1"><input type="checkbox" value={s.id} className="accent-[var(--brand-violet)]" checked={form.skills.includes(s.id)} onChange={(e) => toggle("skills", s.id, e.target.checked)} aria-label={`Skill ${s.name}`} /> {s.name}</label>
                ))}
                {shownSkills.length === 0 && <span className="text-muted-foreground">No skills match.</span>}
              </div>
            </div>
            <div>
              <p>Connectors <span className="text-muted-foreground">(approved MCP servers become tools)</span></p>
              <div className="mt-1 flex flex-wrap gap-2" data-testid="connector-picker">
                {connectors.map((c) => (
                  <label key={c.id} className="flex items-center gap-1.5 rounded-lg border px-2 py-1"><input type="checkbox" className="accent-[var(--brand-violet)]" checked={form.tools.includes(c.id)} onChange={(e) => toggle("tools", c.id, e.target.checked)} aria-label={`Connector ${c.name}`} /> <Plug className="size-3 text-brand-violet-soft" /> {c.name}</label>
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
