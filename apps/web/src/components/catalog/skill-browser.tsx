"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, Search, Sparkles } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Markdown } from "@/components/playground/markdown";
import type { Skill, SkillStats } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export function SkillBrowser({ initial, stats }: { initial: Skill[]; stats: SkillStats }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [source, setSource] = useState("");
  const [rows, setRows] = useState(initial);
  const [detail, setDetail] = useState<Skill | null>(null);

  useEffect(() => {
    const t = setTimeout(async () => {
      const params = new URLSearchParams({ limit: "300" });
      if (q) params.set("q", q);
      if (category) params.set("category", category);
      if (source) params.set("source", source);
      const res = await fetch(`/api/pg/v1/skills?${params}`);
      if (res.ok) setRows((await res.json()).skills);
    }, 200);
    return () => clearTimeout(t);
  }, [q, category, source]);

  const open = async (s: Skill) => {
    const res = await fetch(`/api/pg/v1/skills/${s.id}`);
    setDetail(res.ok ? await res.json() : s);
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
        <h1 className="text-2xl font-semibold tracking-tight">Skills</h1>
        <p className="mt-1 text-sm text-muted-foreground">{stats.total} SKILL.md packs from {Object.keys(stats.by_source).join(" and ")}, each with its source and licence. Attach any of them to an agent in the wizard; they travel with the generated project.</p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <label className="relative">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search skills" aria-label="Search skills" className="h-8 w-64 rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60" />
        </label>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Category">
          {["", ...Object.keys(stats.by_category)].map((c) => (
            <button key={c || "all"} type="button" role="tab" aria-selected={category === c} onClick={() => setCategory(c)} className={cn("h-8 rounded-lg border px-2.5 text-xs", category === c ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground hover:text-foreground")}>
              {c || "All"}{c && <span className="ml-1 font-mono text-[10px] opacity-70">{stats.by_category[c]}</span>}
            </button>
          ))}
        </div>
        <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source" className="h-8 rounded-lg border bg-card px-2 text-xs">
          <option value="">Any source</option>
          {Object.entries(stats.by_source).map(([k, v]) => <option key={k} value={k}>{k} ({v})</option>)}
        </select>
        <span className="ml-auto text-xs text-muted-foreground">{rows.length} shown</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="skill-cards">
        {rows.map((s) => (
          <button key={s.id} type="button" onClick={() => open(s)} className="card-hover flex flex-col rounded-2xl border bg-card p-4 text-left" aria-label={s.name}>
            <div className="flex items-center justify-between gap-2">
              <span className="rounded-md bg-brand-cyan/15 px-1.5 py-0.5 text-[10px] font-medium text-cyan-700 dark:text-cyan-300">{s.category}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{s.words.toLocaleString()} words</span>
            </div>
            <h3 className="mt-2 flex items-center gap-1.5 text-sm font-semibold"><Sparkles className="size-3.5 text-brand-violet-soft" /> {s.name}</h3>
            <p className="mt-1 line-clamp-3 flex-1 text-xs text-muted-foreground">{s.description}</p>
            <p className="mt-2 text-[10px] text-muted-foreground">{s.source.title} · {s.source.license}</p>
          </button>
        ))}
      </div>

      <Dialog open={detail !== null} onOpenChange={(o) => { if (!o) setDetail(null); }}>
        <DialogContent className="sm:max-w-3xl">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle>{detail.name}</DialogTitle>
                <DialogDescription>{detail.description}</DialogDescription>
              </DialogHeader>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <Link href={`/build/agents?skill=${encodeURIComponent(detail.id)}`} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground" aria-label="Attach to a new agent"><Sparkles className="size-3.5" /> Attach to a new agent</Link>
                <a href={detail.source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{detail.source.repo}/{detail.source.path} <ExternalLink className="size-3" /></a>
                <span className="text-muted-foreground">{detail.source.license}{detail.body_truncated ? " · shown truncated" : ""}</span>
              </div>
              <div className="max-h-[55vh] overflow-auto rounded-xl border bg-muted/40 p-4 text-sm" data-testid="skill-body">
                <Markdown text={detail.body ?? detail.preview} />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
