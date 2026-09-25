import Link from "next/link";
import { ArrowRight, Play } from "lucide-react";
import { BLUEPRINTS } from "@/lib/demo-data";
import { CURRENT_BATCH } from "@/lib/nav";

export function BlueprintCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {BLUEPRINTS.map((b) => {
        const live = b.batch <= CURRENT_BATCH;
        return (
          <article key={b.id} className="card-hover beam-border relative flex flex-col rounded-2xl border bg-card p-4">
            <div className="flex items-center justify-between">
              <span className="rounded-md bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-secondary-foreground">{b.family}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{live ? "runnable" : `batch ${b.batch}`}</span>
            </div>
            <h3 className="mt-3 text-base font-semibold tracking-tight">{b.name}</h3>
            <p className="mt-0.5 text-[11.5px] text-brand-violet-soft">{b.pattern}</p>
            <p className="mt-2 flex-1 text-sm text-muted-foreground">{b.summary}</p>
            <div className="mt-3 flex flex-wrap gap-1">
              {b.flavors.map((f) => (
                <span key={f} className="rounded-md border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{f}</span>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-2">
              {live ? (
                <Link href={`/build/agents?blueprint=${b.id}`} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground">
                  <Play className="size-3.5" /> Run on mock data
                </Link>
              ) : (
                <button type="button" disabled className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground opacity-40" title={`Runs from batch ${b.batch}`}>
                  <Play className="size-3.5" /> Run on mock data
                </button>
              )}
              <Link href="/build/agents" className="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs text-muted-foreground hover:text-foreground">
                Details <ArrowRight className="size-3.5" />
              </Link>
            </div>
          </article>
        );
      })}
    </div>
  );
}
