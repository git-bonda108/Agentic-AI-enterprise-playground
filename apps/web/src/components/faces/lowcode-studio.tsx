"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Download, ExternalLink, Plug, Sparkles, Workflow } from "lucide-react";
import { CopyButton } from "@/components/playground/copy-button";
import type { CopilotRecipe, LowcodePlatform, LowcodeStudio, LowcodeTracks } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type Option = { id: string; name: string; category: "Gen AI" | "Agentic AI" };

const STUDIO_BLURB: Record<string, string> = {
  langflow: "Open-source visual builder (MIT). The flow is built from Langflow's own components and attaches the playground as MCP tools.",
  n8n: "Fair-code automation. The workflow wires a Chat Trigger, an AI Agent, memory and the playground as an MCP Client Tool; gated blueprints pause at a review form.",
  copilot: "Microsoft's no-code agent maker. The recipe gives description, instructions, knowledge, tools, triggers, topics and a workflow node map, each with its Microsoft Learn page.",
};

export function LowcodeStudio({ blueprints, initialBlueprint, initialStudio, studios, platforms, mcpUrl }: { blueprints: Option[]; initialBlueprint: string; initialStudio: string; studios: LowcodeStudio[]; platforms: LowcodePlatform[]; mcpUrl: string }) {
  const [blueprint, setBlueprint] = useState(initialBlueprint);
  const [studio, setStudio] = useState(initialStudio);
  const [tracks, setTracks] = useState<LowcodeTracks | null>(null);
  const [loaded, setLoaded] = useState<{ key: string; text: string; recipe: CopilotRecipe | null } | null>(null);
  const key = `${blueprint}:${studio}`;
  const artefact = loaded?.key === key ? loaded.text : "";
  const recipe = loaded?.key === key ? loaded.recipe : null;

  useEffect(() => {
    let stale = false;
    fetch(`/api/pg/v1/lowcode/${blueprint}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (!stale) setTracks(j); }).catch(() => {});
    return () => { stale = true; };
  }, [blueprint]);

  useEffect(() => {
    let stale = false;
    fetch(`/api/pg/v1/lowcode/${blueprint}/${studio}`).then(async (r) => {
      if (!r.ok || stale) return;
      if (studio === "copilot") { const j = (await r.json()) as CopilotRecipe; if (!stale) setLoaded({ key, text: j.markdown, recipe: j }); }
      else { const t = await r.text(); if (!stale) setLoaded({ key, text: t, recipe: null }); }
    }).catch(() => {});
    return () => { stale = true; };
  }, [blueprint, studio, key]);

  const current = studios.find((s) => s.id === studio);
  const selected = blueprints.find((b) => b.id === blueprint);

  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
      <h1 className="text-2xl font-semibold tracking-tight">Low-code studios</h1>
      <p className="mt-1 text-sm text-muted-foreground">Two ways to build every blueprint. The low-code track hands you an importable Langflow flow, an importable n8n workflow or a Copilot Studio recipe; the code track is the notebook, the framework projects and the deploy scripts. Both call the same governed playground.</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-3" data-testid="studio-cards">
        {studios.map((s) => (
          <button key={s.id} type="button" onClick={() => setStudio(s.id)} aria-pressed={studio === s.id} className={cn("card-hover rounded-2xl border bg-card p-3.5 text-left", studio === s.id && "border-brand-violet/60")}>
            <p className="flex items-center gap-1.5 text-sm font-semibold"><Workflow className="size-3.5 text-brand-violet-soft" /> {s.name}</p>
            <p className="mt-1 font-mono text-[10.5px] text-muted-foreground">{s.install}</p>
            <p className="mt-2 text-[11px] text-muted-foreground">{STUDIO_BLURB[s.id]}</p>
          </button>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 text-xs">
        <label className="flex items-center gap-2">Blueprint
          <select value={blueprint} onChange={(e) => setBlueprint(e.target.value)} aria-label="Blueprint to build" className="h-8 rounded-lg border bg-card px-2">
            {(["Gen AI", "Agentic AI"] as const).map((c) => (
              <optgroup key={c} label={c}>{blueprints.filter((b) => b.category === c).map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</optgroup>
            ))}
          </select>
        </label>
        {selected && <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", selected.category === "Agentic AI" ? "bg-brand-pink/15 text-brand-pink" : "bg-brand-cyan/15 text-brand-cyan")} data-testid="studio-category">{selected.category}</span>}
        {current && (
          <a href={`/api/pg/v1/lowcode/${blueprint}/${studio}?download=1`} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground" aria-label={`Download ${current.name} ${current.artefact}`}><Download className="size-3.5" /> Download {current.artefact}</a>
        )}
        {current && <a href={current.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{current.name} import docs <ExternalLink className="size-3" /></a>}
        {current && <a href={current.mcp_docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">MCP in {current.name} <ExternalLink className="size-3" /></a>}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[300px_1fr]">
        <aside className="space-y-3">
          {current && (
            <section className="rounded-2xl border bg-card p-4" aria-label="Steps" data-testid="studio-steps">
              <p className="text-xs font-semibold">Run it in {current.name}</p>
              <ol className="mt-2 list-decimal space-y-1.5 pl-4 text-xs text-muted-foreground">
                {current.steps.map((step) => <li key={step}>{step}</li>)}
              </ol>
              <p className="mt-3 text-[11px] text-muted-foreground">Playground MCP server: <code className="rounded bg-muted px-1">{mcpUrl}</code> <CopyButton text={mcpUrl} /></p>
              <a href={current.install_docs} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-[11px] text-brand-violet-soft hover:underline">Install and licensing <ExternalLink className="size-3" /></a>
            </section>
          )}
          {tracks && (
            <section className="rounded-2xl border bg-card p-4" aria-label="Code track" data-testid="code-track">
              <p className="text-xs font-semibold">Code track</p>
              <p className="mt-1 text-[11px] text-muted-foreground">{tracks.category_blurb}</p>
              <ul className="mt-2 space-y-1 text-xs">
                {tracks.code.map((c) => <li key={c.id}><Link href={c.href} className="text-brand-violet-soft hover:underline">{c.name}</Link> <span className="text-muted-foreground">· {c.blurb}</span></li>)}
              </ul>
            </section>
          )}
          {tracks && tracks.recommended_connectors.length > 0 && (
            <section className="rounded-2xl border bg-card p-4" aria-label="Recommended MCP servers" data-testid="recommended-mcp">
              <p className="flex items-center gap-1.5 text-xs font-semibold"><Plug className="size-3.5 text-brand-violet-soft" /> Most suitable MCP servers</p>
              <ul className="mt-2 space-y-1.5 text-xs">
                {tracks.recommended_connectors.map((c) => (
                  <li key={c.id}>
                    <Link href={`/discover/connectors?q=${encodeURIComponent(c.title)}`} className="font-medium hover:text-brand-violet-soft">{c.title}</Link>
                    <span className="ml-1 rounded bg-muted px-1 text-[10px] text-muted-foreground">{c.approval}</span>
                    <p className="line-clamp-2 text-[11px] text-muted-foreground">{c.description}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>

        <section className="min-w-0" aria-label="Artefact">
          {studio === "copilot" && recipe ? <RecipeView recipe={recipe} /> : (
            <div className="relative">
              <pre className="max-h-[640px] overflow-auto rounded-xl border bg-[#0d0d18] p-4 font-mono text-[11.5px] leading-5 text-slate-100" data-testid="artefact-json">{artefact || "Generating…"}</pre>
              {artefact && <div className="absolute right-2 top-2"><CopyButton text={artefact} /></div>}
            </div>
          )}
        </section>
      </div>

      <section className="mt-8" aria-label="Low-code landscape" data-testid="landscape">
        <h2 className="flex items-center gap-2 text-sm font-semibold"><Sparkles className="size-4 text-brand-violet-soft" /> The low-code landscape</h2>
        <p className="mt-1 text-xs text-muted-foreground">Where each platform fits, how it is licensed, whether it speaks MCP, and what the playground hands you for it. Official links only.</p>
        <div className="mt-3 overflow-x-auto rounded-2xl border bg-card">
          <table className="w-full text-xs">
            <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr><th className="px-3 py-2">Platform</th><th className="px-3 py-2">Licence and hosting</th><th className="px-3 py-2">MCP</th><th className="px-3 py-2">Best for</th><th className="px-3 py-2">From the playground</th><th className="px-3 py-2"></th></tr>
            </thead>
            <tbody>
              {platforms.map((p) => (
                <tr key={p.id} className="border-t align-top">
                  <td className="px-3 py-2"><p className="font-medium">{p.name}</p><p className="text-[10.5px] text-muted-foreground">{p.vendor} · {p.kind}</p></td>
                  <td className="px-3 py-2 text-muted-foreground"><p>{p.licence}</p><p className="mt-1 text-[10.5px]">{p.hosting}</p></td>
                  <td className="px-3 py-2 text-muted-foreground">{p.mcp}</td>
                  <td className="px-3 py-2 text-muted-foreground">{p.best_for}</td>
                  <td className="px-3 py-2 text-muted-foreground">{p.playground}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <a href={p.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Site <ExternalLink className="size-3" /></a>
                    <a href={p.docs} target="_blank" rel="noreferrer" className="ml-2 inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">Docs <ExternalLink className="size-3" /></a>
                    <a href={p.pricing} target="_blank" rel="noreferrer" className="ml-2 inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">Pricing <ExternalLink className="size-3" /></a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border bg-card p-4"><h3 className="text-xs font-semibold">{title}</h3><div className="mt-2 text-xs text-muted-foreground">{children}</div></section>;
}

function RecipeView({ recipe }: { recipe: CopilotRecipe }) {
  return (
    <div className="space-y-3" data-testid="copilot-recipe">
      <Block title="Overview"><p>{recipe.overview}</p><p className="mt-2 text-[11px]">{recipe.orchestration}</p></Block>
      <Block title="Instructions (paste into the agent)">
        <div className="relative"><pre className="max-h-64 overflow-auto rounded-lg bg-[#0d0d18] p-3 font-mono text-[11px] leading-5 text-slate-100 whitespace-pre-wrap">{recipe.instructions}</pre><div className="absolute right-2 top-2"><CopyButton text={recipe.instructions} /></div></div>
      </Block>
      {recipe.knowledge.length > 0 && <Block title="Knowledge"><ul className="space-y-1">{recipe.knowledge.map((k) => <li key={k.dataset}><span className="font-mono text-foreground">{k.dataset}</span>: {k.guidance}</li>)}</ul><a href={recipe.links["Add knowledge"]} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Add knowledge sources <ExternalLink className="size-3" /></a></Block>}
      <Block title="Tools"><ul className="space-y-2">{recipe.tools.map((t) => <li key={t.name}><span className="font-medium text-foreground">{t.name}</span> <span className="rounded bg-muted px-1 text-[10px]">{t.kind}</span><p>{t.why}. {t.how}.{t.url && <> <code className="rounded bg-muted px-1">{t.url}</code></>} <a href={t.docs} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">docs</a></p></li>)}</ul></Block>
      <div className="grid gap-3 sm:grid-cols-2">
        <Block title="Triggers"><ul className="space-y-1">{recipe.triggers.map((t) => <li key={t.name}><span className="font-medium text-foreground">{t.name}</span>: {t.when}</li>)}</ul></Block>
        <Block title="Topics"><ul className="space-y-1">{recipe.topics.map((t) => <li key={t.name}><span className="font-medium text-foreground">{t.name}</span>: {t.purpose}</li>)}</ul></Block>
      </div>
      {recipe.workflow.length > 0 && (
        <Block title="Workflow nodes">
          <table className="w-full text-xs"><thead className="text-left text-[10.5px] uppercase tracking-wider"><tr><th className="py-1 pr-2">Blueprint step</th><th className="py-1 pr-2">Copilot Studio node</th><th className="py-1">How</th></tr></thead>
            <tbody>{recipe.workflow.map((w) => <tr key={w.step} className="border-t align-top"><td className="py-1.5 pr-2 text-foreground">{w.step}</td><td className="py-1.5 pr-2"><a href={w.docs} target="_blank" rel="noreferrer" className="text-brand-violet-soft hover:underline">{w.node}</a></td><td className="py-1.5">{w.how}</td></tr>)}</tbody></table>
        </Block>
      )}
      {recipe.review.length > 0 && <Block title="Human review"><ul className="space-y-1">{recipe.review.map((g) => <li key={g}>{g}</li>)}</ul><a href={recipe.links["Human review"]} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Request for information node <ExternalLink className="size-3" /></a></Block>}
      <Block title="Test and publish"><p>{recipe.evaluation}</p><ul className="mt-2 space-y-1">{recipe.samples.slice(0, 3).map((s) => <li key={s.name}><span className="text-foreground">{s.name}</span> <code className="rounded bg-muted px-1">{JSON.stringify(s.input)}</code></li>)}</ul>
        <div className="mt-2 flex flex-wrap gap-3">{Object.entries(recipe.links).map(([k, v]) => <a key={k} href={v} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{k} <ExternalLink className="size-3" /></a>)}</div>
      </Block>
    </div>
  );
}
