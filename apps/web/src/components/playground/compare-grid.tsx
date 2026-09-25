"use client";

import { Markdown } from "@/components/playground/markdown";
import { TIER_DOT } from "@/components/playground/model-picker";
import { formatTokens, formatUsd, type CatalogModel, type ChatMessage } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export type CompareColumn = { modelId: string; message: ChatMessage | null };

export function CompareGrid({ columns, models, prompt }: { columns: CompareColumn[]; models: CatalogModel[]; prompt: string }) {
  const cols = columns.length;
  return (
    <div className={cn("grid gap-3", cols <= 2 ? "grid-cols-2" : cols === 3 ? "grid-cols-3" : "grid-cols-2 xl:grid-cols-4")} data-testid="compare-grid">
      {columns.map((c) => {
        const m = models.find((x) => x.id === c.modelId);
        const msg = c.message;
        return (
          <section key={c.modelId} className="flex min-h-[240px] flex-col rounded-2xl border bg-card" aria-label={`${m?.name ?? c.modelId} response`}>
            <header className="flex items-center gap-2 border-b px-3 py-2 text-xs">
              <span className={cn("size-1.5 rounded-full", TIER_DOT[m?.tier ?? "Economy"])} />
              <span className="font-medium">{m?.name ?? c.modelId}</span>
              <span className="text-muted-foreground">{m?.provider}</span>
              {msg?.usage && <span className="ml-auto font-mono text-[10.5px] text-muted-foreground">{formatUsd(msg.usage.cost_usd)} · {(msg.usage.latency_ms / 1000).toFixed(1)}s</span>}
            </header>
            <div className="flex-1 overflow-y-auto px-3 py-2">
              {!msg && <p className="text-xs text-muted-foreground">{prompt ? "Waiting to run…" : "Type a prompt and send to compare."}</p>}
              {msg?.content ? <Markdown text={msg.content} /> : msg?.streaming ? <span className="inline-block h-4 w-2 animate-pulse rounded-sm bg-brand-violet-soft" /> : null}
              {msg?.error && <p role="alert" className="mt-2 rounded-lg border border-destructive/40 bg-destructive/10 px-2 py-1 text-xs text-destructive">{msg.error}</p>}
            </div>
            {msg?.usage && (
              <footer className="border-t px-3 py-1.5 text-[10.5px] text-muted-foreground">
                {formatTokens(msg.usage.tokens_in)} in · {formatTokens(msg.usage.tokens_out)} out
              </footer>
            )}
          </section>
        );
      })}
    </div>
  );
}
