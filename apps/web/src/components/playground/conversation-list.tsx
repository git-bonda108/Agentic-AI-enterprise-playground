"use client";

import { Pin, Plus, Search, Trash2 } from "lucide-react";
import type { ConversationSummary } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export function ConversationList({
  items, activeId, query, onQuery, onSelect, onNew, onPin, onDelete,
}: {
  items: ConversationSummary[]; activeId: string | null; query: string;
  onQuery: (q: string) => void; onSelect: (id: string) => void; onNew: () => void; onPin: (c: ConversationSummary) => void; onDelete: (c: ConversationSummary) => void;
}) {
  return (
    <aside aria-label="Conversations" className="flex w-[264px] shrink-0 flex-col border-r bg-sidebar/60">
      <div className="flex items-center gap-2 border-b p-3">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Search conversations"
            aria-label="Search conversations"
            className="h-8 w-full rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60"
          />
        </label>
        <button type="button" onClick={onNew} aria-label="New conversation" className="grid size-8 place-items-center rounded-lg gradient-brand text-white shadow-md shadow-violet-900/30">
          <Plus className="size-4" />
        </button>
      </div>
      <ul className="flex-1 overflow-y-auto p-2">
        {items.length === 0 && <li className="px-2 py-6 text-center text-xs text-muted-foreground">No conversations yet. Say hello.</li>}
        {items.map((c) => (
          <li key={c.id} className="group relative">
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              aria-current={c.id === activeId ? "true" : undefined}
              className={cn("w-full rounded-lg px-2.5 py-2 text-left text-xs transition-colors hover:bg-sidebar-accent/60", c.id === activeId && "bg-sidebar-accent")}
            >
              <span className="flex items-center gap-1.5">
                {c.pinned && <Pin className="size-3 text-brand-violet-soft" />}
                <span className="truncate font-medium">{c.title}</span>
              </span>
              <span className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-muted-foreground">
                <span className="truncate font-mono">{c.model}</span>
                {c.tags.map((t) => <span key={t} className="rounded bg-muted px-1">{t}</span>)}
              </span>
            </button>
            <span className="absolute right-1.5 top-1.5 hidden gap-0.5 group-hover:flex">
              <button type="button" onClick={() => onPin(c)} aria-label={c.pinned ? "Unpin" : "Pin"} className="grid size-6 place-items-center rounded-md hover:bg-muted"><Pin className="size-3" /></button>
              <button type="button" onClick={() => onDelete(c)} aria-label="Delete conversation" className="grid size-6 place-items-center rounded-md hover:bg-muted hover:text-destructive"><Trash2 className="size-3" /></button>
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
