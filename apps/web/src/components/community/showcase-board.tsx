"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, Heart, Loader2, Megaphone, MessageSquare, Search, Sparkles, Trash2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { CustomAgent, RunRecord, ShowcaseDraft, ShowcaseItemRecord } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const KIND_STYLE: Record<string, string> = { agent: "bg-brand-violet/15 text-violet-700 dark:text-violet-300", run: "bg-brand-cyan/15 text-cyan-700 dark:text-cyan-300", conversation: "bg-brand-pink/15 text-pink-700 dark:text-pink-300", suite: "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300" };

export function ShowcaseBoard({ initial, tags: initialTags, myRuns, myAgents, userId, isAdmin }: { initial: ShowcaseItemRecord[]; tags: Record<string, number>; myRuns: RunRecord[]; myAgents: CustomAgent[]; userId: string; isAdmin: boolean }) {
  const [items, setItems] = useState(initial);
  const [tags, setTags] = useState(initialTags);
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("");
  const [sort, setSort] = useState<"new" | "top">("new");
  const [detail, setDetail] = useState<ShowcaseItemRecord | null>(null);
  const [comment, setComment] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [form, setForm] = useState({ kind: "run" as "run" | "agent", ref_id: myRuns[0]?.id ?? myAgents[0]?.id ?? "", title: "", summary: "", outcome: "", tags: "" });
  const [drafting, setDrafting] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const t = setTimeout(async () => {
      const params = new URLSearchParams({ sort });
      if (q) params.set("q", q);
      if (tag) params.set("tag", tag);
      const res = await fetch(`/api/pg/v1/community/showcase?${params}`);
      if (res.ok) { const j = await res.json(); setItems(j.items); setTags(j.tags); }
    }, 200);
    return () => clearTimeout(t);
  }, [q, tag, sort]);

  const open = async (item: ShowcaseItemRecord) => {
    const res = await fetch(`/api/pg/v1/community/showcase/${item.id}`);
    setDetail(res.ok ? await res.json() : item);
  };
  const like = async (item: ShowcaseItemRecord) => {
    const res = await fetch(`/api/pg/v1/community/showcase/${item.id}/like`, { method: "POST" });
    if (!res.ok) return;
    const j = await res.json();
    const apply = (x: ShowcaseItemRecord) => (x.id === item.id ? { ...x, likes: j.likes, liked: j.liked } : x);
    setItems((list) => list.map(apply));
    if (detail?.id === item.id) setDetail(apply(detail));
  };
  const send = async () => {
    if (!detail || !comment.trim()) return;
    const res = await fetch(`/api/pg/v1/community/showcase/${detail.id}/comments`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ body: comment }) });
    if (res.ok) { setDetail(await res.json()); setComment(""); }
  };
  const remove = async (item: ShowcaseItemRecord) => {
    const res = await fetch(`/api/pg/v1/community/showcase/${item.id}`, { method: "DELETE" });
    if (res.ok) { setItems((list) => list.filter((x) => x.id !== item.id)); setDetail(null); }
  };
  const draft = async () => {
    setDrafting(true);
    const agent = myAgents.find((a) => a.id === form.ref_id);
    const body = form.kind === "run" ? { run_id: form.ref_id } : { text: `${agent?.name ?? "An agent"}: ${agent?.description ?? ""}` };
    const res = await fetch("/api/pg/v1/community/showcase/draft", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    setDrafting(false);
    if (!res.ok) { toast.error("The writer agent could not draft this"); return; }
    const d = (await res.json()).draft as ShowcaseDraft;
    setForm((f) => ({ ...f, title: d.title, summary: d.summary, outcome: d.outcome, tags: d.tags.join(", ") }));
    toast.success("Drafted by the showcase writer agent. Edit anything, then publish.");
  };
  const publish = async () => {
    if (form.title.trim().length < 3) { toast.error("Give it a title"); return; }
    setSaving(true);
    const res = await fetch("/api/pg/v1/community/showcase", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ kind: form.kind, ref_id: form.ref_id, title: form.title, summary: form.summary, outcome: form.outcome, tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) }) });
    setSaving(false);
    if (!res.ok) { toast.error("Could not publish"); return; }
    const item = (await res.json()) as ShowcaseItemRecord;
    setItems((list) => [item, ...list]);
    setPublishing(false);
    toast.success("Published to the showcase");
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Community</p>
          <h1 className="text-2xl font-semibold tracking-tight">Showcase</h1>
          <p className="mt-1 text-sm text-muted-foreground">Published agents, runs and results from your colleagues, each with the business outcome in one line. A platform agent drafts the post; you keep the pen.</p>
        </div>
        <Button className="glow-violet" onClick={() => setPublishing(true)} aria-label="Publish to showcase"><Megaphone className="size-4" /> Publish</Button>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <label className="relative">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the showcase" aria-label="Search the showcase" className="h-8 w-64 rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60" />
        </label>
        <div className="flex gap-1" role="tablist" aria-label="Sort">
          {(["new", "top"] as const).map((s) => <button key={s} type="button" role="tab" aria-selected={sort === s} onClick={() => setSort(s)} className={cn("h-8 rounded-lg border px-2.5 text-xs", sort === s ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground")}>{s === "new" ? "Newest" : "Most liked"}</button>)}
        </div>
        <div className="flex flex-wrap gap-1">
          {Object.entries(tags).map(([t, n]) => <button key={t} type="button" onClick={() => setTag(tag === t ? "" : t)} aria-pressed={tag === t} className={cn("h-7 rounded-full border px-2 text-[11px]", tag === t ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground")}>#{t} <span className="opacity-60">{n}</span></button>)}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="showcase-cards">
        {items.map((item) => (
          <article key={item.id} className="card-hover flex flex-col rounded-2xl border bg-card p-4" aria-label={item.title}>
            <div className="flex items-center justify-between gap-2">
              <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", KIND_STYLE[item.kind])}>{item.kind}</span>
              <span className="text-[11px] text-muted-foreground">{item.owner_name} · {item.owner_department}</span>
            </div>
            <button type="button" onClick={() => open(item)} className="mt-2 text-left" aria-label={`Open ${item.title}`}><h3 className="text-base font-semibold">{item.title}</h3></button>
            <p className="mt-1 line-clamp-3 flex-1 text-sm text-muted-foreground">{item.summary}</p>
            {item.outcome && <p className="mt-2 rounded-lg bg-brand-emerald/10 px-2 py-1 text-xs text-emerald-700 dark:text-emerald-300"><Sparkles className="mr-1 inline size-3" />{item.outcome}</p>}
            <div className="mt-3 flex items-center gap-2 text-xs">
              <button type="button" onClick={() => like(item)} aria-label={`${item.liked ? "Unlike" : "Like"} ${item.title}`} aria-pressed={item.liked} className={cn("inline-flex h-7 items-center gap-1 rounded-lg border px-2", item.liked && "border-brand-pink/60 text-brand-pink")}><Heart className={cn("size-3.5", item.liked && "fill-current")} /> {item.likes}</button>
              <span className="text-muted-foreground">{item.views} views</span>
              <span className="ml-auto flex gap-1">{item.tags.map((t) => <span key={t} className="rounded bg-secondary px-1.5 py-0.5 text-[10px]">#{t}</span>)}</span>
            </div>
          </article>
        ))}
        {items.length === 0 && <p className="col-span-full rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">Nothing published yet. Be the first.</p>}
      </div>

      <Dialog open={detail !== null} onOpenChange={(o) => { if (!o) setDetail(null); }}>
        <DialogContent className="sm:max-w-2xl">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle>{detail.title}</DialogTitle>
                <DialogDescription>{detail.owner_name} · {detail.owner_department} · {new Date(detail.created_at).toLocaleDateString()}</DialogDescription>
              </DialogHeader>
              <p className="text-sm">{detail.summary}</p>
              {detail.outcome && <p className="rounded-lg bg-brand-emerald/10 px-2 py-1 text-xs text-emerald-700 dark:text-emerald-300">{detail.outcome}</p>}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <Link href={detail.link} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground"><ExternalLink className="size-3.5" /> Open the {detail.kind}</Link>
                <button type="button" onClick={() => like(detail)} aria-pressed={detail.liked} className={cn("inline-flex h-8 items-center gap-1 rounded-lg border px-2", detail.liked && "border-brand-pink/60 text-brand-pink")}><Heart className={cn("size-3.5", detail.liked && "fill-current")} /> {detail.likes}</button>
                {(detail.owner_id === userId || isAdmin) && <button type="button" onClick={() => remove(detail)} aria-label="Unpublish" className="ml-auto inline-flex items-center gap-1 text-muted-foreground hover:text-destructive"><Trash2 className="size-3.5" /> Unpublish</button>}
              </div>
              <div className="rounded-xl border p-3 text-xs" data-testid="comments">
                <p className="flex items-center gap-1 font-medium"><MessageSquare className="size-3.5" /> Comments</p>
                <ul className="mt-2 space-y-1.5">
                  {(detail.comments ?? []).map((c) => <li key={c.id}><span className="font-medium">{c.user_name}</span> <span className="text-muted-foreground">{c.body}</span></li>)}
                  {(detail.comments ?? []).length === 0 && <li className="text-muted-foreground">No comments yet.</li>}
                </ul>
                <div className="mt-2 flex gap-2">
                  <input value={comment} onChange={(e) => setComment(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") send(); }} aria-label="Comment" placeholder="Say something useful" className="h-8 flex-1 rounded-lg border bg-background px-2" />
                  <Button size="sm" variant="outline" onClick={send} aria-label="Post comment">Post</Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={publishing} onOpenChange={setPublishing}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Publish to the showcase</DialogTitle>
            <DialogDescription>Pick one of your runs or agents. The showcase writer agent drafts a title, summary, outcome and tags from it; edit, then publish.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 text-xs">
            <div className="grid gap-3 sm:grid-cols-2">
              <label>What<select value={form.kind} onChange={(e) => { const kind = e.target.value as "run" | "agent"; setForm({ ...form, kind, ref_id: kind === "run" ? myRuns[0]?.id ?? "" : myAgents[0]?.id ?? "" }); }} aria-label="Kind" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm"><option value="run">A run</option><option value="agent">An agent I built</option></select></label>
              <label>Which<select value={form.ref_id} onChange={(e) => setForm({ ...form, ref_id: e.target.value })} aria-label="Reference" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm">
                {form.kind === "run" ? myRuns.map((r) => <option key={r.id} value={r.id}>{r.blueprint_name} · {new Date(r.created_at).toLocaleString()}</option>) : myAgents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select></label>
            </div>
            <Button variant="outline" size="sm" onClick={draft} disabled={drafting || !form.ref_id} aria-label="Draft with the writer agent">{drafting ? <Loader2 className="size-3.5 animate-spin" /> : <Wand2 className="size-3.5" />} Draft with the writer agent</Button>
            <label>Title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} aria-label="Post title" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" /></label>
            <label>Summary<textarea value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} rows={3} aria-label="Post summary" className="mt-1 w-full rounded-lg border bg-background p-2 text-sm" /></label>
            <label>Outcome in one line<input value={form.outcome} onChange={(e) => setForm({ ...form, outcome: e.target.value })} aria-label="Post outcome" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" placeholder="Saved the controller two hours a week" /></label>
            <label>Tags<input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} aria-label="Post tags" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" placeholder="finance, policies" /></label>
          </div>
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setPublishing(false)}>Cancel</Button><Button className="glow-violet" onClick={publish} disabled={saving} aria-label="Publish post">{saving ? "Publishing…" : "Publish"}</Button></div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
