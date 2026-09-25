"use client";

import { AlertTriangle, Sparkles, User } from "lucide-react";
import { Markdown } from "@/components/playground/markdown";
import { CopyButton } from "@/components/playground/copy-button";
import { formatTokens, formatUsd, type ChatMessage } from "@/lib/playground-types";

export function MessageBubble({ m, modelName }: { m: ChatMessage; modelName?: string }) {
  const isUser = m.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <span className={`mt-1 grid size-7 shrink-0 place-items-center rounded-full ${isUser ? "bg-muted text-foreground" : "gradient-brand text-white"}`} aria-hidden>
        {isUser ? <User className="size-3.5" /> : <Sparkles className="size-3.5" />}
      </span>
      <div className={`min-w-0 max-w-[85%] ${isUser ? "rounded-2xl rounded-tr-sm bg-secondary px-4 py-2.5 text-secondary-foreground" : ""}`}>
        {isUser ? (
          <p className="whitespace-pre-wrap text-[14.5px] leading-7">{m.content}</p>
        ) : (
          <>
            {m.content ? <Markdown text={m.content} /> : m.streaming ? <span className="inline-block h-4 w-2 animate-pulse rounded-sm bg-brand-violet-soft" aria-label="Generating" /> : null}
            {m.error && (
              <p role="alert" className="mt-2 flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {m.error}
              </p>
            )}
            {m.usage && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground" data-testid="usage-chip">
                <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono">{modelName ?? m.usage.model}</span>
                {m.usage.routed && <span className="rounded-md bg-brand-violet/15 px-1.5 py-0.5 text-[10px] text-violet-700 dark:text-violet-300" title={`Smart routing chose the ${m.usage.routed_tier} tier`}>smart · saved {formatUsd(m.usage.savings_usd ?? 0)}</span>}
                <span>{formatTokens(m.usage.tokens_in)} in · {formatTokens(m.usage.tokens_out)} out</span>
                {m.usage.tokens_cached > 0 && <span className="text-brand-emerald">{formatTokens(m.usage.tokens_cached)} cached</span>}
                <span className="font-medium text-foreground">{formatUsd(m.usage.cost_usd)}</span>
                <span>{(m.usage.latency_ms / 1000).toFixed(1)}s</span>
                <CopyButton text={m.content} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
