"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { ExternalLink, Play, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RunDialog } from "@/components/agents/run-dialog";
import type { BlueprintManifest } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const FAMILY_STYLE: Record<string, string> = { Domain: "bg-brand-violet/15 text-violet-700 dark:text-violet-300", Role: "bg-brand-cyan/15 text-cyan-700 dark:text-cyan-300" };

export function BlueprintGrid({ blueprints }: { blueprints: BlueprintManifest[] }) {
  const params = useSearchParams();
  // A ?blueprint= parameter opens the run dialog on arrival; the page keys this component on it so a new link remounts.
  const requested = blueprints.find((b) => b.id === params.get("blueprint")) ?? null;
  const [open, setOpen] = useState<BlueprintManifest | null>(requested);

  const launch = (bp: BlueprintManifest) => setOpen(bp);

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="blueprint-grid">
        {blueprints.map((b) => (
          <article key={b.id} className="card-hover beam-border relative flex flex-col rounded-2xl border bg-card p-4" aria-label={b.name}>
            <div className="flex items-center justify-between">
              <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", FAMILY_STYLE[b.family] ?? "bg-secondary text-secondary-foreground")}>{b.family}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{b.graph.nodes.length} steps · {b.review_gates.length ? "human gate" : "no gate"}</span>
            </div>
            <h3 className="mt-3 text-base font-semibold tracking-tight">{b.name}</h3>
            <p className="mt-0.5 text-[11.5px] text-brand-violet-soft">{b.pattern}</p>
            <p className="mt-2 flex-1 text-sm text-muted-foreground">{b.summary}</p>
            <div className="mt-3 flex flex-wrap gap-1">
              {Object.entries(b.tiers).map(([k, v]) => <span key={k} className="rounded-md border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground" title={`${k} step`}>{k}: {v}</span>)}
            </div>
            <div className="mt-3 flex flex-wrap gap-1">
              {b.flavors.map((f) => <span key={f} className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{f}</span>)}
            </div>
            <div className="mt-4 flex items-center gap-2">
              <Button size="sm" className="glow-violet" onClick={() => launch(b)} aria-label={`Run ${b.name}`}><Play className="size-3.5" /> Run on mock data</Button>
              {b.review_gates.length > 0 && <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground"><UserCheck className="size-3" /> pauses for you</span>}
              {b.links.origin && <a href={b.links.origin} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground">origin <ExternalLink className="size-3" /></a>}
            </div>
          </article>
        ))}
      </div>

      {open && <RunDialog key={open.id} target={{ id: open.id, name: open.name, description: open.description, samples: open.samples, input_schema: open.input_schema, datasets: open.datasets }} onClose={() => setOpen(null)} />}
    </>
  );
}
