"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, Database, Download, ExternalLink, Globe } from "lucide-react";
import { CopyButton } from "@/components/playground/copy-button";
import type { DataSource, DatasetInfo } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type Props = { datasets: DatasetInfo[]; sources: DataSource[]; notebookPaths: Record<string, string>; blueprintNames: Record<string, string> };

function DatasetCard({ d, notebookPath, blueprintNames }: { d: DatasetInfo; notebookPath?: string; blueprintNames: Record<string, string> }) {
  const [tab, setTab] = useState<"columns" | "preview">("columns");
  return (
    <section className="rounded-2xl border bg-card p-4" aria-label={d.title} data-testid={`dataset-${d.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold"><Database className="size-4 text-brand-cyan" /> {d.title}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{d.source}</p>
        </div>
        <span className="font-mono text-[11px] text-muted-foreground">{d.rows} {d.shape === "keyed" ? "keys" : "rows"} · {d.file}</span>
      </div>
      <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <span>Licence: <a href={d.licence.url} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">{d.licence.name}</a></span>
        {d.modeled_on && <span>Modelled on: <a href={d.modeled_on.url} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">{d.modeled_on.name}</a> (<a href={d.modeled_on.licence_url} target="_blank" rel="noreferrer" className="hover:underline">{d.modeled_on.licence}</a>)</span>}
      </p>
      <p className="mt-1 flex flex-wrap gap-x-2 text-[11px] text-muted-foreground">
        Used by: {d.used_by.map((b) => <Link key={b} href={`/build/agents?blueprint=${b}`} className="text-brand-violet-soft hover:underline">{blueprintNames[b] ?? b}</Link>)}
        {notebookPath && <Link href={`/build/notebooks?source=${encodeURIComponent(notebookPath)}`} className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline"><BookOpen className="size-3" /> Open in a notebook</Link>}
      </p>
      <div className="mt-3 flex items-center gap-1 text-[11px]" role="tablist" aria-label={`${d.title} views`}>
        <button type="button" role="tab" aria-selected={tab === "columns"} onClick={() => setTab("columns")} className={cn("h-6 rounded-md px-2", tab === "columns" ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground")}>Columns</button>
        <button type="button" role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")} className={cn("h-6 rounded-md px-2", tab === "preview" ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground")}>Preview</button>
      </div>
      {tab === "columns" ? (
        <table className="mt-2 w-full text-[11px]" data-testid={`columns-${d.id}`}>
          <thead className="text-left uppercase tracking-wider text-muted-foreground"><tr><th className="py-1 pr-2">Column</th><th className="py-1 pr-2">Type</th><th className="py-1">Example</th></tr></thead>
          <tbody>
            {d.columns.map((c) => <tr key={c.name} className="border-t"><td className="py-1 pr-2 font-mono">{c.name}</td><td className="py-1 pr-2 text-muted-foreground">{c.type}</td><td className="max-w-[240px] truncate py-1 font-mono text-muted-foreground">{String(c.example)}</td></tr>)}
          </tbody>
        </table>
      ) : (
        <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-muted p-2 font-mono text-[10.5px] text-muted-foreground">{JSON.stringify(d.preview.slice(0, 3), null, 1)}</pre>
      )}
      <div className="relative mt-3">
        <pre className="overflow-auto rounded-lg border bg-[#0d0d18] p-2 pr-16 font-mono text-[11px] leading-5 text-slate-100">{d.snippet}</pre>
        <div className="absolute right-1.5 top-1.5"><CopyButton text={d.snippet} /></div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <a href={`/api/pg${d.download.csv}`} className="inline-flex h-7 items-center gap-1 rounded-lg border px-2.5 hover:bg-muted" aria-label={`Download ${d.title} as CSV`}><Download className="size-3" /> CSV</a>
        <a href={`/api/pg${d.download.json}`} className="inline-flex h-7 items-center gap-1 rounded-lg border px-2.5 hover:bg-muted" aria-label={`Download ${d.title} as JSON`}><Download className="size-3" /> JSON</a>
      </div>
    </section>
  );
}

function SourceCard({ s }: { s: DataSource }) {
  const snippet = [s.install, s.python].filter(Boolean).join("\n");
  return (
    <section className="rounded-2xl border bg-card p-4" aria-label={s.name}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold"><Globe className="size-4 text-brand-emerald" /> {s.name}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{s.kind}. {s.good_for}.</p>
        </div>
        <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex h-7 shrink-0 items-center gap-1 rounded-lg bg-primary px-2.5 text-xs font-medium text-primary-foreground" aria-label={`Open ${s.name}`}>Open <ExternalLink className="size-3" /></a>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">Licence: {s.licence}. <a href={s.docs} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">Loader docs</a></p>
      {snippet && (
        <div className="relative mt-3">
          <pre className="overflow-auto rounded-lg border bg-[#0d0d18] p-2 pr-16 font-mono text-[11px] leading-5 text-slate-100">{snippet}</pre>
          <div className="absolute right-1.5 top-1.5"><CopyButton text={snippet} /></div>
        </div>
      )}
    </section>
  );
}

export function DatasetsBrowser({ datasets, sources, notebookPaths, blueprintNames }: Props) {
  const [tab, setTab] = useState<"mock" | "sources">("mock");
  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Build</p>
      <h1 className="text-2xl font-semibold tracking-tight">Datasets</h1>
      <p className="mt-1 text-sm text-muted-foreground">Mock datasets every blueprint can run against safely, generated deterministically and modelled on public sets, with their columns, downloads and a notebook snippet. When you are ready for real data, the trusted sources tab lists where to get it and the loader each source publishes.</p>
      <div className="mt-4 flex w-fit items-center gap-1 rounded-lg border bg-card p-0.5 text-xs" role="tablist" aria-label="Dataset kind">
        <button type="button" role="tab" aria-selected={tab === "mock"} onClick={() => setTab("mock")} className={cn("h-7 rounded-md px-3", tab === "mock" ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground")}>Mock datasets ({datasets.length})</button>
        <button type="button" role="tab" aria-selected={tab === "sources"} onClick={() => setTab("sources")} className={cn("h-7 rounded-md px-3", tab === "sources" ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground")}>Trusted sources ({sources.length})</button>
      </div>
      {tab === "mock" ? (
        <div className="mt-4 grid gap-4 md:grid-cols-2" data-testid="datasets">
          {datasets.map((d) => <DatasetCard key={d.id} d={d} notebookPath={d.notebook ? notebookPaths[d.notebook] : undefined} blueprintNames={blueprintNames} />)}
        </div>
      ) : (
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="sources">
          {sources.map((s) => <SourceCard key={s.id} s={s} />)}
        </div>
      )}
    </div>
  );
}
