"use client";

import Link from "next/link";

import { useEffect, useState } from "react";
import { BookOpen, CheckCircle2, Cloud, Code2, ExternalLink, NotebookPen, Play, Search, XCircle } from "lucide-react";
import { RunDialog, type RunTarget } from "@/components/agents/run-dialog";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { CatalogEntry, CatalogStats } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const FAMILY_STYLE: Record<string, string> = {
  Domain: "bg-brand-violet/15 text-violet-700 dark:text-violet-300", Role: "bg-brand-cyan/15 text-cyan-700 dark:text-cyan-300",
  Topology: "bg-brand-pink/15 text-pink-700 dark:text-pink-300", Persona: "bg-brand-amber/15 text-amber-700 dark:text-amber-300",
  "Low-code": "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300", Cloud: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
};
const FAMILY_BLURB: Record<string, string> = {
  All: "Everything in the catalog", Domain: "Runnable business workflows from the Agent Hub", Role: "Engineering and review roles imported from everything-claude-code",
  Topology: "Coordination patterns imported from ruflo", Persona: "Leadership and review personas imported from gstack",
  "Low-code": "Copilot Studio style templates: instructions, knowledge, starter prompts", Cloud: "Mirrors of AWS AgentCore, Google ADK and Microsoft Foundry samples",
};

export function CatalogBrowser({ initial, families, stats }: { initial: CatalogEntry[]; families: string[]; stats: CatalogStats }) {
  const [family, setFamily] = useState("All");
  const [category, setCategory] = useState<"All" | "Gen AI" | "Agentic AI">("All");
  const [q, setQ] = useState("");
  const [onlyRunnable, setOnlyRunnable] = useState(false);
  const [entries, setEntries] = useState(initial);
  const [detail, setDetail] = useState<CatalogEntry | null>(null);
  const [runTarget, setRunTarget] = useState<RunTarget | null>(null);

  useEffect(() => {
    let stale = false;  // a slower, older response must not overwrite a newer one
    const t = setTimeout(async () => {
      const params = new URLSearchParams();
      if (family !== "All") params.set("family", family);
      if (category !== "All") params.set("category", category);
      if (q) params.set("q", q);
      if (onlyRunnable) params.set("runnable", "true");
      const res = await fetch(`/api/pg/v1/catalog?${params}`);
      const body = res.ok ? await res.json() : null;
      if (body && !stale) setEntries(body.entries);
    }, 200);
    return () => { stale = true; clearTimeout(t); };
  }, [family, category, q, onlyRunnable]);

  const openDetail = async (e: CatalogEntry) => {
    const res = await fetch(`/api/pg/v1/catalog/${e.id}`);
    setDetail(res.ok ? await res.json() : e);
  };
  const runEntry = (e: CatalogEntry) =>
    setRunTarget({
      id: e.id, name: e.name, description: e.summary,
      samples: e.samples ?? [{ name: "Ask the agent", input: { task: e.starter_prompts?.[0] ?? "Describe what you do and how you would approach a typical task." } }],
      input_schema: e.input_schema ?? { task: "text", context: "optional text" }, datasets: e.knowledge ?? [],
    });

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
          <h1 className="text-2xl font-semibold tracking-tight">Blueprints</h1>
          <p className="mt-1 text-sm text-muted-foreground">{stats.total} blueprints across six families, {stats.green} curated green, {stats.runnable} runnable today. Sources: {stats.sources.join(", ")}.</p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="rounded-full bg-brand-emerald/15 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300" data-testid="green-count">{stats.green} green</span>
          <span className="rounded-full bg-muted px-2.5 py-1 font-medium text-muted-foreground">{stats.red} red</span>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <label className="relative">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search blueprints" aria-label="Search blueprints" className="h-8 w-60 rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60" />
        </label>
        <div className="flex gap-1" role="tablist" aria-label="Category" data-testid="category-tabs">
          {(["All", "Gen AI", "Agentic AI"] as const).map((c) => (
            <button key={c} type="button" role="tab" aria-selected={category === c} onClick={() => setCategory(c)} className={cn("h-8 rounded-lg border px-2.5 text-xs font-medium", category === c ? "border-brand-pink/60 bg-brand-pink/10" : "bg-card text-muted-foreground hover:text-foreground")} title={c === "Gen AI" ? "One model call with instructions and knowledge" : c === "Agentic AI" ? "Several steps, tools, review or coordination" : "Every blueprint"}>
              {c}{c !== "All" && <span className="ml-1 font-mono text-[10px] opacity-70">{stats.by_category?.[c] ?? 0}</span>}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Family">
          {["All", ...families].map((f) => (
            <button key={f} type="button" role="tab" aria-selected={family === f} onClick={() => setFamily(f)} className={cn("h-8 rounded-lg border px-2.5 text-xs", family === f ? "border-brand-violet/60 bg-secondary text-secondary-foreground" : "bg-card text-muted-foreground hover:text-foreground")}>
              {f}{f !== "All" && <span className="ml-1 font-mono text-[10px] opacity-70">{stats.by_family[f] ?? 0}</span>}
            </button>
          ))}
        </div>
        <label className="flex h-8 items-center gap-1.5 rounded-lg border bg-card px-2.5 text-xs">
          <input type="checkbox" checked={onlyRunnable} onChange={(e) => setOnlyRunnable(e.target.checked)} className="accent-[var(--brand-violet)]" /> Runnable only
        </label>
        <span className="ml-auto text-xs text-muted-foreground">{FAMILY_BLURB[family]}</span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" data-testid="catalog-grid">
        {entries.length === 0 && <p className="col-span-full py-10 text-center text-sm text-muted-foreground">Nothing matches.</p>}
        {entries.map((e) => (
          <article key={e.id} className="card-hover flex flex-col rounded-2xl border bg-card p-3.5" aria-label={e.name}>
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-1">
                <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", FAMILY_STYLE[e.family])}>{e.family}</span>
                <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", e.category === "Agentic AI" ? "bg-brand-pink/15 text-brand-pink" : "bg-brand-cyan/15 text-brand-cyan")} data-testid="category-badge">{e.category}</span>
              </span>
              <span className={cn("inline-flex items-center gap-1 text-[10px]", e.curation.status === "green" ? "text-brand-emerald" : e.curation.status === "red" ? "text-brand-rose" : "text-muted-foreground")} title={e.curation.reasons.join("; ") || "Curated"}>
                {e.curation.status === "green" ? <CheckCircle2 className="size-3" /> : <XCircle className="size-3" />} {e.curation.status}
              </span>
            </div>
            <button type="button" onClick={() => openDetail(e)} className="mt-2 text-left">
              <h3 className="text-sm font-semibold tracking-tight hover:text-brand-violet-soft">{e.name}</h3>
            </button>
            <p className="mt-1 line-clamp-3 flex-1 text-xs text-muted-foreground">{e.summary}</p>
            <p className="mt-2 truncate font-mono text-[10px] text-muted-foreground">{e.source.title}{e.group ? ` · ${e.group}` : ""} · {e.source.license}</p>
            <div className="mt-3 grid grid-cols-4 gap-1 text-[10.5px]" aria-label="Faces">
              <Face icon={Play} label="Run" enabled={e.runnable} onClick={() => runEntry(e)} hint={e.runnable ? "Run with governed models" : "Not runnable here"} />
              <Face icon={NotebookPen} label="Notebook" enabled={e.runnable} href={e.runnable ? `/build/notebooks?blueprint=${e.id}` : undefined} sameTab hint={e.runnable ? "Open as a notebook" : "Not runnable here"} />
              <Face icon={Code2} label="Code" enabled href={e.source.title.startsWith("Playground") || e.family === "Low-code" ? `/discover/frameworks?blueprint=${e.id}` : e.source.url} sameTab={e.source.title.startsWith("Playground") || e.family === "Low-code"} hint={e.source.title.startsWith("Playground") || e.family === "Low-code" ? "Get it as a project in five SDKs" : "Open the source"} />
              <Face icon={Cloud} label="Deploy" enabled={e.runnable || Boolean(e.links?.deploy)} href={e.runnable ? `/discover/clouds?blueprint=${e.id}` : e.links?.deploy} sameTab={e.runnable} hint={e.runnable ? "Deploy commands for four clouds" : e.links?.deploy ? "Provider runtime guide" : "Not deployable"} />
            </div>
          </article>
        ))}
      </div>

      <Dialog open={detail !== null} onOpenChange={(o) => { if (!o) setDetail(null); }}>
        <DialogContent className="sm:max-w-3xl">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle>{detail.name}</DialogTitle>
                <DialogDescription>{detail.summary}</DialogDescription>
              </DialogHeader>
              <div className="flex flex-wrap gap-1 text-[10.5px]">
                {detail.tags.map((t) => <span key={t} className="rounded-md bg-muted px-1.5 py-0.5 text-muted-foreground">{t}</span>)}
                {detail.tools.slice(0, 8).map((t) => <span key={t} className="rounded-md border px-1.5 py-0.5 font-mono text-muted-foreground">{t}</span>)}
              </div>
              <pre className="max-h-80 overflow-auto rounded-xl border bg-[#0d0d18] p-3 font-mono text-[11.5px] leading-5 text-slate-100 whitespace-pre-wrap" data-testid="entry-instructions">{detail.instructions ?? detail.instructions_preview}</pre>
              {detail.runnable && (
                <div className="rounded-xl border p-3" data-testid="build-tracks">
                  <p className="text-xs font-semibold">Build it your way <span className="ml-1 font-normal text-muted-foreground">{detail.category} blueprint</span></p>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2 text-xs">
                    <div>
                      <p className="text-[10.5px] font-medium uppercase tracking-wider text-muted-foreground">Low-code track</p>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {[["langflow", "Langflow flow"], ["n8n", "n8n workflow"], ["copilot", "Copilot Studio recipe"]].map(([id, label]) => (
                          <Link key={id} href={`/discover/low-code?blueprint=${detail.id}&studio=${id}`} className="rounded-md border px-2 py-1 hover:border-brand-violet/40">{label}</Link>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[10.5px] font-medium uppercase tracking-wider text-muted-foreground">Code track</p>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        <Link href={`/build/notebooks?blueprint=${detail.id}`} className="rounded-md border px-2 py-1 hover:border-brand-violet/40">Notebook</Link>
                        <Link href={`/discover/frameworks?blueprint=${detail.id}`} className="rounded-md border px-2 py-1 hover:border-brand-violet/40">Frameworks</Link>
                        <Link href={`/discover/clouds?blueprint=${detail.id}`} className="rounded-md border px-2 py-1 hover:border-brand-violet/40">Deploy</Link>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <a href={detail.source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline"><BookOpen className="size-3.5" /> {detail.source.repo} · {detail.source.license} <ExternalLink className="size-3" /></a>
                {detail.curation.reasons.length > 0 && <span className="text-muted-foreground">Curator: {detail.curation.reasons.join("; ")}</span>}
                {detail.runnable && <button type="button" onClick={() => { setDetail(null); runEntry(detail); }} className="ml-auto inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground"><Play className="size-3.5" /> Run</button>}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {runTarget && <RunDialog key={runTarget.id} target={runTarget} onClose={() => setRunTarget(null)} />}
    </div>
  );
}

function Face({ icon: Icon, label, enabled, onClick, href, hint, sameTab = false }: { icon: React.ComponentType<{ className?: string }>; label: string; enabled: boolean; onClick?: () => void; href?: string; hint: string; sameTab?: boolean }) {
  const cls = cn("flex h-8 flex-col items-center justify-center gap-0.5 rounded-lg border", enabled ? "hover:border-brand-violet/50 hover:text-foreground" : "opacity-40");
  if (href && enabled) return <a href={href} target={sameTab ? undefined : "_blank"} rel={sameTab ? undefined : "noreferrer"} className={cls} title={hint} aria-label={`${label}: ${hint}`}><Icon className="size-3.5" />{label}</a>;
  return <button type="button" disabled={!enabled} onClick={onClick} className={cls} title={hint} aria-label={`${label}: ${hint}`}><Icon className="size-3.5" />{label}</button>;
}
