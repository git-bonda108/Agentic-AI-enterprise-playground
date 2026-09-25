"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, FileUp, FolderGit2, Globe, Loader2, MessageSquareQuote, Plus, Search, Table2, Trash2, Waypoints } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Markdown } from "@/components/playground/markdown";
import { CodeGraph } from "@/components/knowledge/code-graph";
import type { DatasetInfo, EmbeddingModel, GraphEdge, GraphNode, KnowledgeDocument, KnowledgeSpace, RunRecord, SearchHit } from "@/lib/playground-types";
import { formatUsd } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type SpaceDetail = KnowledgeSpace & { documents: KnowledgeDocument[]; can_edit: boolean };
const VISIBILITY: Record<string, string> = { private: "Only me", department: "My department", org: "Whole organization" };

export function KnowledgeWorkbench({ spaces: initial, models, datasets, initialDetail, repoRoot }: { spaces: KnowledgeSpace[]; models: EmbeddingModel[]; datasets: DatasetInfo[]; initialDetail: SpaceDetail | null; repoRoot: string }) {
  const router = useRouter();
  const [spaces, setSpaces] = useState(initial);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", visibility: "private", embedding_model: "local-hash" });
  const [detail, setDetail] = useState<SpaceDetail | null>(initialDetail);
  const [busy, setBusy] = useState<string | null>(null);
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [answer, setAnswer] = useState<RunRecord | null>(null);
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [inputs, setInputs] = useState({ title: "", text: "", url: "", dataset: datasets[0]?.id ?? "policies", repo: repoRoot, query: "", question: "" });

  const load = useCallback(async (id: string) => {
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${id}`);
    if (res.ok) { setDetail(await res.json()); setHits(null); setAnswer(null); setGraph(null); }
  }, []);
  const select = (s: KnowledgeSpace) => { router.replace(`/build/knowledge?space=${s.id}`); load(s.id); };

  const create = async () => {
    if (form.name.trim().length < 2) { toast.error("Give the space a name"); return; }
    const res = await fetch("/api/pg/v1/knowledge/spaces", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(form) });
    if (!res.ok) { toast.error("Could not create the space"); return; }
    const s = (await res.json()) as KnowledgeSpace;
    setSpaces((list) => [s, ...list]);
    setCreating(false);
    setForm({ name: "", description: "", visibility: "private", embedding_model: "local-hash" });
    select(s);
    toast.success(`${s.name} is ready`);
  };

  const refreshList = async () => { const r = await fetch("/api/pg/v1/knowledge/spaces"); if (r.ok) setSpaces((await r.json()).spaces); };

  const ingest = async (kind: "text" | "url" | "file" | "dataset" | "repo", body: Record<string, unknown>) => {
    if (!detail) return;
    setBusy(kind);
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${detail.id}/documents/${kind}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    setBusy(null);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "Import failed"); return; }
    const d = (await res.json()) as KnowledgeDocument & { summary?: { files: number; symbols: number; edges: number } };
    toast.success(d.summary ? `Mapped ${d.summary.files} files, ${d.summary.symbols} symbols, ${d.summary.edges} edges` : `${d.title}: ${d.chunk_count} chunks embedded`);
    await load(detail.id);
    refreshList();
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    const buf = await file.arrayBuffer();
    let binary = "";
    const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    await ingest("file", { filename: file.name, content_base64: btoa(binary) });
  };

  const removeDoc = async (d: KnowledgeDocument) => {
    if (!detail) return;
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${detail.id}/documents/${d.id}`, { method: "DELETE" });
    if (res.ok) { await load(detail.id); refreshList(); }
  };
  const removeSpace = async () => {
    if (!detail) return;
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${detail.id}`, { method: "DELETE" });
    if (res.ok) { setSpaces((l) => l.filter((s) => s.id !== detail.id)); setDetail(null); router.replace("/build/knowledge"); }
  };

  const search = async () => {
    if (!detail || !inputs.query.trim()) return;
    setBusy("search");
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${detail.id}/search`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ query: inputs.query, k: 6 }) });
    setBusy(null);
    if (res.ok) setHits((await res.json()).hits);
  };
  const ask = async () => {
    if (!detail || inputs.question.trim().length < 3) return;
    setBusy("ask");
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${detail.id}/ask`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ question: inputs.question }) });
    setBusy(null);
    if (!res.ok) { const j = await res.json().catch(() => ({})); toast.error(j.detail ?? "The question could not be answered"); return; }
    setAnswer(await res.json());
  };
  const loadGraph = async () => {
    if (!detail) return;
    const res = await fetch(`/api/pg/v1/knowledge/spaces/${detail.id}/graph`);
    if (res.ok) setGraph(await res.json());
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Build</p>
          <h1 className="text-2xl font-semibold tracking-tight">Knowledge</h1>
          <p className="mt-1 text-sm text-muted-foreground">Knowledge Spaces over your documents, pages, datasets and repositories. Hybrid search, cited answers, and a map of any codebase. Embeddings are metered like every other call.</p>
        </div>
        <Button className="glow-violet" onClick={() => setCreating(true)} aria-label="New Knowledge Space"><Plus className="size-4" /> New space</Button>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[300px_1fr]">
        <aside className="space-y-2" data-testid="space-list">
          {spaces.length === 0 && <p className="rounded-2xl border border-dashed p-5 text-center text-xs text-muted-foreground">No spaces yet. Create one and drop in a policy, a web page, a dataset or a repository.</p>}
          {spaces.map((s) => (
            <button key={s.id} type="button" onClick={() => select(s)} aria-label={`Open space ${s.name}`} className={cn("card-hover w-full rounded-2xl border bg-card p-3 text-left", detail?.id === s.id && "border-brand-violet/60")}>
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 text-sm font-semibold"><BookOpen className="size-3.5 text-brand-violet-soft" /> {s.name}</span>
                <span className="rounded-md bg-secondary px-1.5 py-0.5 text-[10px] text-secondary-foreground">{VISIBILITY[s.visibility]}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{s.description || "No description"}</p>
              <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">{s.doc_count} docs · {s.chunk_count} chunks · {s.embedding_name}</p>
            </button>
          ))}
        </aside>

        <section className="min-w-0 rounded-2xl border bg-card p-4" data-testid="space-detail">
          {!detail ? (
            <div className="grid h-full min-h-[320px] place-items-center text-center text-sm text-muted-foreground"><p>Select a space, or create one.</p></div>
          ) : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">{detail.name}</h2>
                  <p className="text-xs text-muted-foreground">{detail.description || "No description"} · {VISIBILITY[detail.visibility]} · owner {detail.owner_name ?? detail.owner_id} · {detail.embedding_name}</p>
                </div>
                {detail.can_edit && <button type="button" onClick={removeSpace} aria-label="Delete space" className="grid size-8 place-items-center rounded-lg hover:bg-muted hover:text-destructive"><Trash2 className="size-4" /></button>}
              </div>

              <Tabs defaultValue="add" className="mt-4">
                <TabsList>
                  <TabsTrigger value="add"><Plus className="mr-1 size-3" /> Add content</TabsTrigger>
                  <TabsTrigger value="search"><Search className="mr-1 size-3" /> Search</TabsTrigger>
                  <TabsTrigger value="ask"><MessageSquareQuote className="mr-1 size-3" /> Ask</TabsTrigger>
                  <TabsTrigger value="graph" onClick={loadGraph}><Waypoints className="mr-1 size-3" /> Graph</TabsTrigger>
                </TabsList>

                <TabsContent value="add">
                  {detail.can_edit ? (
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-xl border p-3">
                        <p className="flex items-center gap-1.5 text-xs font-semibold"><BookOpen className="size-3.5" /> Paste text</p>
                        <input value={inputs.title} onChange={(e) => setInputs({ ...inputs, title: e.target.value })} aria-label="Document title" placeholder="Title" className="mt-2 h-8 w-full rounded-lg border bg-background px-2 text-xs" />
                        <textarea value={inputs.text} onChange={(e) => setInputs({ ...inputs, text: e.target.value })} aria-label="Document text" rows={5} placeholder="Paste a policy, a runbook, meeting notes…" className="mt-2 w-full rounded-lg border bg-background p-2 text-xs" />
                        <Button size="sm" className="mt-2" disabled={busy !== null || !inputs.title || !inputs.text} onClick={() => ingest("text", { title: inputs.title, text: inputs.text })} aria-label="Add text">{busy === "text" ? <Loader2 className="size-3.5 animate-spin" /> : <Plus className="size-3.5" />} Add text</Button>
                      </div>
                      <div className="space-y-3">
                        <div className="rounded-xl border p-3">
                          <p className="flex items-center gap-1.5 text-xs font-semibold"><FileUp className="size-3.5" /> Upload a file</p>
                          <p className="mt-1 text-[11px] text-muted-foreground">PDF, Word, Markdown, text, CSV, JSON or HTML.</p>
                          <input type="file" aria-label="Upload file" accept=".pdf,.docx,.md,.txt,.csv,.json,.html" onChange={(e) => onFile(e.target.files?.[0])} className="mt-2 block w-full text-xs file:mr-2 file:rounded-md file:border file:bg-card file:px-2 file:py-1 file:text-xs" />
                        </div>
                        <div className="rounded-xl border p-3">
                          <p className="flex items-center gap-1.5 text-xs font-semibold"><Globe className="size-3.5" /> Web page</p>
                          <div className="mt-2 flex gap-2">
                            <input value={inputs.url} onChange={(e) => setInputs({ ...inputs, url: e.target.value })} aria-label="Page URL" placeholder="https://…" className="h-8 flex-1 rounded-lg border bg-background px-2 text-xs" />
                            <Button size="sm" variant="outline" disabled={busy !== null || !inputs.url} onClick={() => ingest("url", { url: inputs.url })} aria-label="Import page">{busy === "url" ? <Loader2 className="size-3.5 animate-spin" /> : "Import"}</Button>
                          </div>
                        </div>
                      </div>
                      <div className="rounded-xl border p-3">
                        <p className="flex items-center gap-1.5 text-xs font-semibold"><Table2 className="size-3.5" /> Mock dataset</p>
                        <p className="mt-1 text-[11px] text-muted-foreground">One chunk per record, so answers cite the record id.</p>
                        <div className="mt-2 flex gap-2">
                          <select value={inputs.dataset} onChange={(e) => setInputs({ ...inputs, dataset: e.target.value })} aria-label="Dataset" className="h-8 flex-1 rounded-lg border bg-background px-2 text-xs">
                            {datasets.map((d) => <option key={d.id} value={d.id}>{d.title} ({d.rows})</option>)}
                          </select>
                          <Button size="sm" variant="outline" disabled={busy !== null} onClick={() => ingest("dataset", { dataset: inputs.dataset })} aria-label="Import dataset">{busy === "dataset" ? <Loader2 className="size-3.5 animate-spin" /> : "Import"}</Button>
                        </div>
                      </div>
                      <div className="rounded-xl border p-3">
                        <p className="flex items-center gap-1.5 text-xs font-semibold"><FolderGit2 className="size-3.5" /> Repository map</p>
                        <p className="mt-1 text-[11px] text-muted-foreground">A GitHub URL or a local path. Code becomes a graph of files, classes, functions and imports, plus searchable chunks.</p>
                        <div className="mt-2 flex gap-2">
                          <input value={inputs.repo} onChange={(e) => setInputs({ ...inputs, repo: e.target.value })} aria-label="Repository source" className="h-8 flex-1 rounded-lg border bg-background px-2 font-mono text-[11px]" />
                          <Button size="sm" variant="outline" disabled={busy !== null || !inputs.repo} onClick={() => ingest("repo", { source: inputs.repo })} aria-label="Map repository">{busy === "repo" ? <Loader2 className="size-3.5 animate-spin" /> : "Map"}</Button>
                        </div>
                      </div>
                    </div>
                  ) : <p className="text-xs text-muted-foreground">You can search and ask here; only the owner or an admin can add content.</p>}

                  <table className="mt-4 w-full text-xs" data-testid="documents-table">
                    <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground"><tr><th className="py-1">Document</th><th>Source</th><th className="text-right">Chunks</th><th className="text-right">Tokens</th><th className="text-right">Cost</th><th></th></tr></thead>
                    <tbody>
                      {detail.documents.map((d) => (
                        <tr key={d.id} className="border-t">
                          <td className="py-1.5 font-medium">{d.title}</td>
                          <td className="text-muted-foreground">{d.source_type}{d.has_graph ? " · graph" : ""}</td>
                          <td className="text-right font-mono">{d.chunk_count}</td>
                          <td className="text-right font-mono">{d.tokens.toLocaleString()}</td>
                          <td className="text-right font-mono">{formatUsd(d.cost_usd)}</td>
                          <td className="text-right">{detail.can_edit && <button type="button" onClick={() => removeDoc(d)} aria-label={`Remove ${d.title}`} className="rounded p-1 hover:bg-muted hover:text-destructive"><Trash2 className="size-3.5" /></button>}</td>
                        </tr>
                      ))}
                      {detail.documents.length === 0 && <tr><td colSpan={6} className="py-3 text-center text-muted-foreground">Nothing here yet.</td></tr>}
                    </tbody>
                  </table>
                </TabsContent>

                <TabsContent value="search">
                  <div className="flex gap-2">
                    <input value={inputs.query} onChange={(e) => setInputs({ ...inputs, query: e.target.value })} onKeyDown={(e) => { if (e.key === "Enter") search(); }} aria-label="Search query" placeholder="What are you looking for?" className="h-9 flex-1 rounded-lg border bg-background px-3 text-sm" />
                    <Button onClick={search} disabled={busy !== null} aria-label="Search space">{busy === "search" ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />} Search</Button>
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">Hybrid: cosine over embeddings and BM25 over keywords, fused by reciprocal rank.</p>
                  <ol className="mt-3 space-y-2" data-testid="search-hits">
                    {hits?.map((h) => (
                      <li key={h.chunk_id} className="rounded-xl border p-3">
                        <div className="flex items-center justify-between text-[11px]"><span className="font-mono text-brand-violet-soft">[{h.cite}]</span><span className="font-mono text-muted-foreground">score {h.score} · dense {h.dense} · bm25 {h.sparse}</span></div>
                        <p className="mt-1 whitespace-pre-wrap text-xs">{h.text.slice(0, 600)}{h.text.length > 600 ? "…" : ""}</p>
                        {h.meta.file ? <p className="mt-1 font-mono text-[10px] text-muted-foreground">{String(h.meta.file)}{h.meta.line ? `:${String(h.meta.line)}` : ""}</p> : null}
                      </li>
                    ))}
                    {hits && hits.length === 0 && <li className="text-xs text-muted-foreground">No matching chunks.</li>}
                  </ol>
                </TabsContent>

                <TabsContent value="ask">
                  <div className="flex gap-2">
                    <input value={inputs.question} onChange={(e) => setInputs({ ...inputs, question: e.target.value })} onKeyDown={(e) => { if (e.key === "Enter") ask(); }} aria-label="Question" placeholder="Ask a question answered only from this space" className="h-9 flex-1 rounded-lg border bg-background px-3 text-sm" />
                    <Button onClick={ask} disabled={busy !== null} aria-label="Ask space">{busy === "ask" ? <Loader2 className="size-4 animate-spin" /> : <MessageSquareQuote className="size-4" />} Ask</Button>
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">Runs the Knowledge Q&amp;A blueprint: retrieve, answer with citations, verify every citation. Metered as an agent run.</p>
                  {answer && (
                    <div className="mt-3 rounded-xl border p-4" data-testid="ask-answer">
                      <div className="flex flex-wrap items-center gap-2 text-[11px]">
                        <span className={cn("rounded-md px-1.5 py-0.5 font-medium", answer.output?.grounded ? "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300" : "bg-brand-amber/15 text-amber-700 dark:text-amber-300")}>{answer.output?.grounded ? "Grounded" : "Check citations"}</span>
                        <span className="font-mono text-muted-foreground">{formatUsd(answer.cost_usd)} · {answer.tokens_in + answer.tokens_out} tokens</span>
                        <a href={`/operate/runs/${answer.id}`} className="text-brand-violet-soft hover:underline">Open run</a>
                      </div>
                      <div className="mt-2 text-sm"><Markdown text={String(answer.output?.answer_md ?? "")} /></div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="graph">
                  {graph ? (graph.nodes.length ? <CodeGraph nodes={graph.nodes} edges={graph.edges} /> : <p className="text-xs text-muted-foreground">No repository has been mapped into this space yet. Use Add content, then Repository map.</p>) : <p className="text-xs text-muted-foreground">Loading…</p>}
                </TabsContent>
              </Tabs>
            </>
          )}
        </section>
      </div>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Knowledge Space</DialogTitle>
            <DialogDescription>Pick who can see it and which embedding model indexes it. The model choice sets the cost per million tokens.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 text-xs">
            <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} aria-label="Space name" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" placeholder="Finance policies" /></label>
            <label>Description<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} aria-label="Space description" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm" placeholder="What goes in here and who it is for" /></label>
            <label>Visibility<select value={form.visibility} onChange={(e) => setForm({ ...form, visibility: e.target.value })} aria-label="Visibility" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm">{Object.entries(VISIBILITY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Embedding model<select value={form.embedding_model} onChange={(e) => setForm({ ...form, embedding_model: e.target.value })} aria-label="Embedding model" className="mt-1 h-9 w-full rounded-lg border bg-background px-2 text-sm">{models.map((m) => <option key={m.id} value={m.id} disabled={!m.available}>{m.name} · {m.price_per_m === 0 ? "free" : `$${m.price_per_m}/M tokens`}{m.available ? "" : " · key not set"}</option>)}</select></label>
            <p className="text-muted-foreground">{models.find((m) => m.id === form.embedding_model)?.note}</p>
          </div>
          <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setCreating(false)}>Cancel</Button><Button className="glow-violet" onClick={create} aria-label="Create space">Create space</Button></div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
