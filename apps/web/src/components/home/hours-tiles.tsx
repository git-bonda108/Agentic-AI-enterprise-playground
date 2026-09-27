import Link from "next/link";
import { ArrowDownRight, ArrowUpRight, Bot, Clock, MessagesSquare, NotebookPen } from "lucide-react";
import type { UsageHours } from "@/lib/playground-types";

const TILES = [
  { key: "chat", label: "Chat hours", href: "/build/playground", icon: MessagesSquare, accent: "text-brand-violet-soft", blurb: "Playground and compare" },
  { key: "agent", label: "Agent hours", href: "/build/agents", icon: Bot, accent: "text-brand-cyan", blurb: "Blueprint runs, evaluations and canaries" },
  { key: "notebook", label: "Notebook hours", href: "/build/notebooks", icon: NotebookPen, accent: "text-brand-emerald", blurb: "Browser and sandbox sessions" },
] as const;

export function formatHours(h: number): string {
  if (h < 1) return `${Math.round(h * 60)} min`;
  return `${h.toFixed(h >= 10 ? 0 : 1)} h`;
}

export function HoursTiles({ hours }: { hours: UsageHours | null | undefined }) {
  if (!hours) return null;
  const delta = (key: string) => {
    const cur = hours.window[key] ?? 0;
    const prev = hours.previous[key] ?? 0;
    if (prev === 0) return cur > 0 ? { pct: null, up: true } : null;
    return { pct: Math.round(((cur - prev) / prev) * 100), up: cur >= prev };
  };
  const other = (hours.window.sdk ?? 0) + (hours.window.other ?? 0);
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-testid="hours-tiles">
      {TILES.map((t) => {
        const d = delta(t.key);
        return (
          <Link key={t.key} href={t.href} className="card-hover rounded-2xl border bg-card p-4" data-testid={`hours-${t.key}`}>
            <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground"><t.icon className={`size-3.5 ${t.accent}`} /> {t.label}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{formatHours(hours.window[t.key] ?? 0)}</p>
            <p className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground">
              {d && (d.up ? <ArrowUpRight className="size-3 text-brand-emerald" /> : <ArrowDownRight className="size-3 text-brand-rose" />)}
              {d ? (d.pct === null ? "new this window" : `${d.pct >= 0 ? "+" : ""}${d.pct}% vs the previous ${hours.days} days`) : `none in the last ${hours.days} days`}
              {" · "}{hours.people[t.key] ?? 0} {hours.people[t.key] === 1 ? "person" : "people"}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">{t.blurb}</p>
          </Link>
        );
      })}
      <div className="rounded-2xl border bg-card p-4" data-testid="hours-total">
        <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground"><Clock className="size-3.5 text-brand-pink" /> All features</p>
        <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{formatHours(hours.window.total ?? 0)}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">{formatHours(hours.previous.total ?? 0)} in the previous {hours.days} days · {formatHours(other)} through the SDK gateway and other features</p>
        <p className="mt-1 text-[11px] text-muted-foreground">Hours come from ledger sessions: a gap of more than 30 minutes starts a new session.</p>
      </div>
    </div>
  );
}
