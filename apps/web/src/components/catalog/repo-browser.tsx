"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, GitFork, Search, Star } from "lucide-react";
import type { Repo, RepoCategory } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const fmt = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10_000 ? 0 : 1)}k` : String(n));
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// Deterministic formatting: browser locales abbreviate months differently from Node, which broke hydration.
const when = (iso: string) => { if (!iso) return ""; const d = new Date(iso); return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`; };

export function RepoBrowser({ initial, categories, generatedAt, starsTotal }: { initial: Repo[]; categories: RepoCategory[]; generatedAt: string | null; starsTotal: number }) {
  const [category, setCategory] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState(initial);

  useEffect(() => {
    let stale = false;
    const t = setTimeout(async () => {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (q) params.set("q", q);
      const res = await fetch(`/api/pg/v1/repos?${params}`);
      const body = res.ok ? await res.json() : null;
      if (body && !stale) setRows(body.repos);
    }, 200);
    return () => { stale = true; clearTimeout(t); };
  }, [category, q]);

  const groups = categories.filter((c) => !category || c.id === category);

  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
      <h1 className="text-2xl font-semibold tracking-tight">Popular Git repos</h1>
      <p className="mt-1 text-sm text-muted-foreground">The repositories behind the playground and the ones worth knowing next to it: what each is for, how it relates to what you can do here, and the official link. Stars, licences and activity come from GitHub{generatedAt ? ` (snapshot ${when(generatedAt)})` : ""}.</p>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <label className="relative">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search repositories" aria-label="Search repositories" className="h-8 w-60 rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60" />
        </label>
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Category" data-testid="repo-categories">
          <button type="button" role="tab" aria-selected={category === ""} onClick={() => setCategory("")} className={cn("h-8 rounded-lg border px-2.5 text-xs", category === "" ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground hover:text-foreground")}>All</button>
          {categories.map((c) => (
            <button key={c.id} type="button" role="tab" aria-selected={category === c.id} onClick={() => setCategory(c.id)} className={cn("h-8 rounded-lg border px-2.5 text-xs", category === c.id ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground hover:text-foreground")}>
              {c.id}<span className="ml-1 font-mono text-[10px] opacity-70">{c.count}</span>
            </button>
          ))}
        </div>
        <span className="ml-auto text-xs text-muted-foreground">{rows.length} repositories · {fmt(starsTotal)} stars combined</span>
      </div>

      {groups.map((g) => {
        const items = rows.filter((r) => r.category === g.id);
        if (!items.length) return null;
        const reference = g.id === "Reference implementations";
        return (
          <section key={g.id} className="mt-6" aria-label={g.id} data-testid={`repo-group-${g.id.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
            <h2 className="text-sm font-semibold">{g.id} <span className="ml-1 text-xs font-normal text-muted-foreground">{g.blurb}</span></h2>
            <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {items.map((r) => (
                <article key={r.id} className={cn("card-hover flex flex-col rounded-2xl border bg-card p-3.5", reference && "border-brand-pink/30")} aria-label={r.full_name}>
                  <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
                    <span className="inline-flex items-center gap-2"><span className="inline-flex items-center gap-0.5"><Star className="size-3" /> {fmt(r.stars)}</span><span className="inline-flex items-center gap-0.5"><GitFork className="size-3" /> {fmt(r.forks)}</span></span>
                    <span className="font-mono">{r.license}{r.language ? ` · ${r.language}` : ""}</span>
                  </div>
                  <h3 className="mt-2 text-sm font-semibold"><a href={r.url} target="_blank" rel="noreferrer" className="hover:text-brand-violet-soft">{r.full_name}</a></h3>
                  <p className="mt-1 line-clamp-3 flex-1 text-xs text-muted-foreground">{r.blurb}</p>
                  <p className="mt-2 text-[11px]"><span className="rounded-md bg-muted px-1.5 py-0.5 text-muted-foreground">{r.relation}</span></p>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
                    <a href={r.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">GitHub <ExternalLink className="size-3" /></a>
                    {r.homepage && <a href={r.homepage} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">Site <ExternalLink className="size-3" /></a>}
                    <Link href={r.playground_href} className="text-muted-foreground hover:text-foreground">{reference ? "Rate in the Showcase" : "In the playground"}</Link>
                    <span className="ml-auto text-muted-foreground">{r.archived ? "archived" : `updated ${when(r.pushed_at)}`}</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        );
      })}
      {rows.length === 0 && <p className="mt-6 rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">No repositories match.</p>}
    </div>
  );
}
