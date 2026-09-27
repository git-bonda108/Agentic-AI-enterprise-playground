"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, Clock, Search } from "lucide-react";
import { HOWTO } from "@/lib/howto";
import { findNavItem } from "@/lib/nav";
import type { DocGuideMeta, DocSearchHit } from "@/lib/playground-types";

type Props = { sections: string[]; guides: DocGuideMeta[] };

export function DocsHub({ sections, guides }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<DocSearchHit[] | null>(null);

  useEffect(() => {
    const q = query.trim();
    let stale = false;
    const t = setTimeout(() => {
      if (q.length < 2) { setHits(null); return; }
      fetch(`/api/pg/v1/docs/search?q=${encodeURIComponent(q)}`).then((r) => (r.ok ? r.json() : { hits: [] })).then((j) => { if (!stale) setHits(j.hits ?? []); }).catch(() => {});
    }, 200);
    return () => { stale = true; clearTimeout(t); };
  }, [query]);

  const pageGuides = Object.entries(HOWTO).map(([path, h]) => ({ path, title: findNavItem(path)?.item.title ?? path, howto: h }));

  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Home</p>
      <h1 className="text-2xl font-semibold tracking-tight">Documentation</h1>
      <p className="mt-1 text-sm text-muted-foreground">Every guide to the playground, served here rather than from a repository: how to use each page, how agents, notebooks, datasets and clouds work, the API, and how the platform is built, secured and deployed.</p>

      <label className="mt-4 flex h-10 max-w-xl items-center gap-2 rounded-xl border bg-card px-3 text-sm">
        <Search className="size-4 text-muted-foreground" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the guides, for example: budget, azd deploy, personal token" aria-label="Search the documentation" className="w-full bg-transparent outline-none placeholder:text-muted-foreground" />
      </label>

      {hits && (
        <div className="mt-3 rounded-2xl border bg-card p-3" data-testid="doc-search-results">
          {hits.length === 0 && <p className="text-xs text-muted-foreground">Nothing mentions that yet. Try another word, or browse the sections below.</p>}
          <ul className="space-y-2">
            {hits.map((h, i) => (
              <li key={`${h.slug}-${i}`}>
                <Link href={`/docs/${h.slug}${h.anchor ? `#${h.anchor}` : ""}`} className="block rounded-lg px-2 py-1.5 hover:bg-muted">
                  <p className="text-xs font-medium">{h.title}{h.section ? <span className="text-muted-foreground"> · {h.section}</span> : null}</p>
                  <p className="text-[11px] text-muted-foreground">{h.snippet}</p>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {sections.map((section) => (
        <section key={section} className="mt-6" aria-label={section}>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">{section}</h2>
          <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3" data-testid={`docs-${section.toLowerCase().replace(/\s+/g, "-")}`}>
            {guides.filter((g) => g.section === section).map((g) => (
              <Link key={g.slug} href={`/docs/${g.slug}`} className="card-hover rounded-2xl border bg-card p-4">
                <p className="flex items-center gap-2 text-sm font-semibold"><BookOpen className="size-4 text-brand-violet-soft" /> {g.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{g.summary}</p>
                <p className="mt-2 flex items-center gap-2 text-[11px] text-muted-foreground"><Clock className="size-3" /> {g.minutes} min · {g.headings.length} sections · opens with {g.page_label}</p>
              </Link>
            ))}
          </div>
        </section>
      ))}

      <section className="mt-8" aria-label="Page guides">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Page guides</h2>
        <p className="mt-1 text-xs text-muted-foreground">The same steps the How to button shows on each page, in one place.</p>
        <div className="mt-2 grid gap-3 md:grid-cols-2" data-testid="page-guides">
          {pageGuides.map((p) => (
            <div key={p.path} className="rounded-2xl border bg-card p-4">
              <p className="text-sm font-semibold"><Link href={p.path} className="hover:underline">{p.title}</Link> <span className="font-normal text-muted-foreground">· {p.howto.title}</span></p>
              <p className="mt-1 text-xs text-muted-foreground">{p.howto.intro}</p>
              <ol className="mt-2 list-decimal space-y-1 pl-4 text-xs">
                {p.howto.steps.map((s, i) => <li key={i}>{s.text}{s.href && s.label && <> <Link href={s.href} className="text-brand-violet-soft hover:underline">{s.label}</Link></>}</li>)}
              </ol>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
