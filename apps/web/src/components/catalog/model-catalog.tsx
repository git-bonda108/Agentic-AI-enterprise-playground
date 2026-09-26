"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpDown, BookOpen, Check, ExternalLink, LayoutGrid, Lock, Rows3, Search, Sparkles, KeyRound } from "lucide-react";
import { formatTokens, PROVIDER_ART, type CatalogModel } from "@/lib/playground-types";
import { cn } from "@/lib/utils";
import { openKeysDrawer } from "@/components/shell/keys-drawer";

const TIERS = ["Frontier", "Premium", "Workhorse", "Economy"] as const;
const TIER_STYLE: Record<string, string> = {
  Frontier: "bg-brand-violet/15 text-violet-700 dark:text-violet-300",
  Premium: "bg-brand-pink/15 text-pink-700 dark:text-pink-300",
  Workhorse: "bg-brand-cyan/15 text-cyan-700 dark:text-cyan-300",
  Economy: "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300",
};

type Sort = "price" | "name" | "context";

export function ModelCatalog({ models, smartEnabled }: { models: (CatalogModel & { allowed: boolean })[]; smartEnabled: boolean }) {
  const [q, setQ] = useState("");
  const [provider, setProvider] = useState<string>("All");
  const [tier, setTier] = useState<string>("All");
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [view, setView] = useState<"grid" | "table">("grid");
  const [sort, setSort] = useState<Sort>("price");

  const providers = useMemo(() => ["All", ...Array.from(new Set(models.map((m) => m.provider)))], [models]);
  const rows = useMemo(() => {
    const list = models.filter((m) =>
      (provider === "All" || m.provider === provider) &&
      (tier === "All" || m.tier === tier) &&
      (!onlyAvailable || m.available) &&
      (q === "" || `${m.name} ${m.provider} ${m.tags.join(" ")}`.toLowerCase().includes(q.toLowerCase())),
    );
    return list.sort((a, b) =>
      sort === "price" ? a.input_per_m + a.output_per_m - (b.input_per_m + b.output_per_m) : sort === "context" ? b.context - a.context : a.name.localeCompare(b.name),
    );
  }, [models, provider, tier, onlyAvailable, q, sort]);

  const maxPrice = Math.max(...models.map((m) => m.output_per_m), 1);

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
          <h1 className="text-2xl font-semibold tracking-tight">Models</h1>
          <p className="mt-1 text-sm text-muted-foreground">{models.length} models across {providers.length - 1} providers, one price sheet. Greyed models need a key or a policy change.</p>
        </div>
        {smartEnabled && (
          <Link href="/build/playground?model=smart" className="inline-flex h-9 items-center gap-2 rounded-lg gradient-brand px-3.5 text-sm font-medium text-white shadow-md shadow-violet-900/30">
            <Sparkles className="size-4" /> Try Smart routing
          </Link>
        )}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <label className="relative">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search models" aria-label="Search models" className="h-8 w-56 rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60" />
        </label>
        <div className="flex flex-wrap gap-1" role="group" aria-label="Provider filter">
          {providers.map((p) => (
            <button key={p} type="button" onClick={() => setProvider(p)} aria-pressed={provider === p} className={cn("h-8 rounded-lg border px-2.5 text-xs", provider === p ? "border-brand-violet/60 bg-secondary text-secondary-foreground" : "bg-card text-muted-foreground hover:text-foreground")}>{p}</button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1" role="group" aria-label="Tier filter">
          {["All", ...TIERS].map((t) => (
            <button key={t} type="button" onClick={() => setTier(t)} aria-pressed={tier === t} className={cn("h-8 rounded-lg border px-2.5 text-xs", tier === t ? "border-brand-violet/60 bg-secondary text-secondary-foreground" : "bg-card text-muted-foreground hover:text-foreground")}>{t}</button>
          ))}
        </div>
        <label className="flex h-8 items-center gap-1.5 rounded-lg border bg-card px-2.5 text-xs">
          <input type="checkbox" checked={onlyAvailable} onChange={(e) => setOnlyAvailable(e.target.checked)} className="accent-[var(--brand-violet)]" /> Available only
        </label>
        <div className="ml-auto flex items-center gap-1">
          <button type="button" onClick={() => setSort(sort === "price" ? "name" : sort === "name" ? "context" : "price")} className="flex h-8 items-center gap-1 rounded-lg border bg-card px-2.5 text-xs text-muted-foreground hover:text-foreground" aria-label="Change sort">
            <ArrowUpDown className="size-3.5" /> {sort === "price" ? "Cheapest first" : sort === "name" ? "By name" : "Largest context"}
          </button>
          <button type="button" onClick={() => setView("grid")} aria-label="Grid view" aria-pressed={view === "grid"} className={cn("grid size-8 place-items-center rounded-lg border", view === "grid" ? "bg-secondary" : "bg-card")}><LayoutGrid className="size-3.5" /></button>
          <button type="button" onClick={() => setView("table")} aria-label="Table view" aria-pressed={view === "table"} className={cn("grid size-8 place-items-center rounded-lg border", view === "table" ? "bg-secondary" : "bg-card")}><Rows3 className="size-3.5" /></button>
        </div>
      </div>

      {view === "grid" ? (
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" data-testid="model-grid">
          {rows.map((m) => (
            <article key={m.id} className={cn("card-hover flex flex-col overflow-hidden rounded-2xl border bg-card", (!m.available || !m.allowed) && "opacity-70")} aria-label={m.name}>
              <div className="relative h-20" style={{ backgroundImage: PROVIDER_ART[m.provider] ?? PROVIDER_ART.Anthropic }}>
                <div className="absolute inset-0 grid-bg opacity-30" aria-hidden />
                <span className="absolute left-3 top-3 rounded-md bg-black/25 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur">{m.provider}</span>
                <span className="absolute right-3 top-3 rounded-md bg-white/90 px-1.5 py-0.5 text-[10px] font-semibold text-slate-800">{m.lifecycle}</span>
              </div>
              <div className="flex flex-1 flex-col p-3.5">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold">{m.name}</p>
                  <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${TIER_STYLE[m.tier]}`}>{m.tier}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {m.tags.map((t) => <span key={t} className="rounded-md bg-muted px-1.5 py-0.5 text-[10.5px] text-muted-foreground">{t}</span>)}
                </div>
                <div className="mt-3 space-y-1 text-[11px]">
                  <PriceBar label="Input" value={m.input_per_m} max={maxPrice} />
                  <PriceBar label="Output" value={m.output_per_m} max={maxPrice} />
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
                  <dt>Context</dt><dd className="font-mono text-foreground">{formatTokens(m.context)}</dd>
                  <dt>Cached input</dt><dd className="font-mono text-foreground">{m.cached_input_per_m !== null ? `$${m.cached_input_per_m}` : "—"}</dd>
                  <dt>Capabilities</dt><dd className="text-foreground">{m.capabilities.join(", ")}</dd>
                </dl>
                <div className="mt-auto flex items-center gap-2 pt-3">
                  {m.available && m.allowed ? (
                    <Link href={`/build/playground?model=${m.id}`} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground">Try in playground</Link>
                  ) : (
                    !m.available ? (
                      <button type="button" onClick={() => openKeysDrawer(m.provider)} className="inline-flex h-8 items-center gap-1 rounded-lg border border-brand-amber/50 px-3 text-xs text-brand-amber hover:bg-brand-amber/10" title={`Add your own ${m.provider} key to use ${m.name}`}>
                        <KeyRound className="size-3" /> Add your {m.provider} key
                      </button>
                    ) : (
                      <span className="inline-flex h-8 items-center gap-1 rounded-lg border px-3 text-xs text-muted-foreground" title="Not allowed for your role">
                        <Lock className="size-3" /> Policy
                      </span>
                    )
                  )}
                  <a href={m.docs_url} target="_blank" rel="noreferrer" className="ml-auto inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs text-muted-foreground hover:text-foreground" aria-label={`${m.provider} documentation`}>
                    <BookOpen className="size-3.5" /> Docs <ExternalLink className="size-3" />
                  </a>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="mt-5 overflow-x-auto rounded-2xl border bg-card" data-testid="model-table">
          <table className="w-full text-xs">
            <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-3 py-2">Model</th><th className="px-3 py-2">Provider</th><th className="px-3 py-2">Tier</th><th className="px-3 py-2 text-right">Input / 1M</th><th className="px-3 py-2 text-right">Output / 1M</th><th className="px-3 py-2 text-right">Cached</th><th className="px-3 py-2 text-right">Context</th><th className="px-3 py-2">Status</th><th className="px-3 py-2"></th></tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.id} className="border-t">
                  <td className="px-3 py-2 font-medium">{m.name}</td>
                  <td className="px-3 py-2 text-muted-foreground">{m.provider}</td>
                  <td className="px-3 py-2"><span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${TIER_STYLE[m.tier]}`}>{m.tier}</span></td>
                  <td className="px-3 py-2 text-right font-mono">${m.input_per_m}</td>
                  <td className="px-3 py-2 text-right font-mono">${m.output_per_m}</td>
                  <td className="px-3 py-2 text-right font-mono">{m.cached_input_per_m !== null ? `$${m.cached_input_per_m}` : "—"}</td>
                  <td className="px-3 py-2 text-right font-mono">{formatTokens(m.context)}</td>
                  <td className="px-3 py-2">{m.available ? (m.allowed ? <span className="inline-flex items-center gap-1 text-brand-emerald"><Check className="size-3" /> {m.key_source === "personal" ? "Your key" : "Ready"}</span> : <span className="text-brand-amber">Policy</span>) : <button type="button" onClick={() => openKeysDrawer(m.provider)} className="text-brand-amber hover:underline">Add key</button>}</td>
                  <td className="px-3 py-2 text-right">{m.available && m.allowed && <Link href={`/build/playground?model=${m.id}`} className="text-brand-violet-soft hover:underline">Try</Link>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PriceBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.max(3, Math.min(100, (Math.log10(value + 0.01) + 2) / (Math.log10(max + 0.01) + 2) * 100));
  return (
    <div className="flex items-center gap-2">
      <span className="w-12 text-muted-foreground">{label}</span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"><span className="block h-full rounded-full gradient-brand" style={{ width: `${pct}%` }} /></span>
      <span className="w-14 text-right font-mono">${value}</span>
    </div>
  );
}
