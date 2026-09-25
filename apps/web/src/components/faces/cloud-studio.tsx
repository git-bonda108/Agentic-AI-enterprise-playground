"use client";

import { useEffect, useState } from "react";
import { Cloud, Download, ExternalLink } from "lucide-react";
import { CopyButton } from "@/components/playground/copy-button";
import type { CloudInfo } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

type Option = { id: string; name: string };
type Script = CloudInfo & { script: string; filename: string };

export function CloudStudio({ clouds, blueprints, initialBlueprint }: { clouds: CloudInfo[]; blueprints: Option[]; initialBlueprint: string }) {
  const [blueprint, setBlueprint] = useState(initialBlueprint);
  const [cloud, setCloud] = useState(clouds[0]?.id ?? "foundry");
  const [script, setScript] = useState<Script | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/pg/v1/blueprints/${blueprint}/deploy/${cloud}`).then((r) => (r.ok ? r.json() : null)).then((j) => { if (!cancelled) setScript(j); });
    return () => { cancelled = true; };
  }, [blueprint, cloud]);

  const download = () => {
    if (!script) return;
    const blob = new Blob([script.script], { type: "text/x-shellscript" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = script.filename;
    a.click();
  };

  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
      <h1 className="text-2xl font-semibold tracking-tight">Clouds</h1>
      <p className="mt-1 text-sm text-muted-foreground">Deploy a blueprint to a provider runtime with the exact commands. The pricing unit is shown before you run anything, and the spend lands on your cloud bill, not on the playground.</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid="cloud-cards">
        {clouds.map((c) => (
          <button key={c.id} type="button" onClick={() => setCloud(c.id)} aria-pressed={cloud === c.id} className={cn("card-hover rounded-2xl border bg-card p-3.5 text-left", cloud === c.id && "border-brand-violet/60")}>
            <p className="flex items-center gap-2 text-sm font-semibold"><Cloud className="size-4 text-brand-cyan" /> {c.name}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{c.runtime}</p>
            <p className="mt-2 text-[11px]"><span className="font-medium">Pricing:</span> {c.pricing}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">Needs: {c.prereq}</p>
          </button>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 text-xs">
        <label className="flex items-center gap-2">Blueprint
          <select value={blueprint} onChange={(e) => setBlueprint(e.target.value)} aria-label="Blueprint to deploy" className="h-8 rounded-lg border bg-card px-2">
            {blueprints.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </label>
        <button type="button" onClick={download} disabled={!script} className="inline-flex h-8 items-center gap-1 rounded-lg bg-primary px-3 font-medium text-primary-foreground disabled:opacity-50" aria-label="Download deploy script"><Download className="size-3.5" /> Download script</button>
        {script && <a href={script.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{script.name} guide <ExternalLink className="size-3" /></a>}
        {script && <a href={script.pricing_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">pricing <ExternalLink className="size-3" /></a>}
      </div>

      {script && (
        <div className="relative mt-4">
          <pre className="max-h-[520px] overflow-auto rounded-xl border bg-[#0d0d18] p-4 font-mono text-[12px] leading-6 text-slate-100" data-testid="deploy-script">{script.script}</pre>
          <div className="absolute right-2 top-2"><CopyButton text={script.script} /></div>
        </div>
      )}
    </div>
  );
}
