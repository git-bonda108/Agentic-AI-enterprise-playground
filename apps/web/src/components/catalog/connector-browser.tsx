"use client";

import { useEffect, useState } from "react";
import { Check, ExternalLink, Plug, RefreshCw, Search, ShieldBan, ShieldCheck, Wifi, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { CopyButton } from "@/components/playground/copy-button";
import type { Connector, ConnectorStats, ProbeResult } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const APPROVAL_STYLE: Record<string, string> = {
  approved: "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300",
  pending: "bg-brand-amber/15 text-amber-700 dark:text-amber-300",
  blocked: "bg-brand-rose/15 text-rose-700 dark:text-rose-300",
};
const TRANSPORTS = ["", "remote", "npm", "pypi", "oci", "mcpb"];

export function ConnectorBrowser({ initial, stats: initialStats, isAdmin }: { initial: Connector[]; stats: ConnectorStats; isAdmin: boolean }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [transport, setTransport] = useState("");
  const [approval, setApproval] = useState("");
  const [rows, setRows] = useState(initial);
  const [total, setTotal] = useState(initial.length);
  const [stats, setStats] = useState(initialStats);
  const [detail, setDetail] = useState<Connector | null>(null);
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  const [probing, setProbing] = useState(false);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    let stale = false;  // a slower, older response must not overwrite a newer one
    const t = setTimeout(async () => {
      const params = new URLSearchParams({ limit: "60" });
      if (q) params.set("q", q);
      if (category) params.set("category", category);
      if (transport) params.set("transport", transport);
      if (approval) params.set("approval", approval);
      const res = await fetch(`/api/pg/v1/connectors?${params}`);
      if (res.ok) { const j = await res.json(); if (!stale) { setRows(j.connectors); setTotal(j.total); } }
    }, 200);
    return () => { stale = true; clearTimeout(t); };
  }, [q, category, transport, approval]);

  const refreshStats = async () => { const r = await fetch("/api/pg/v1/connectors/stats"); if (r.ok) setStats(await r.json()); };

  const open = (c: Connector) => { setDetail(c); setProbe(null); };
  const runProbe = async (c: Connector) => {
    setProbing(true);
    const res = await fetch(`/api/pg/v1/connectors/${c.id}/probe`, { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
    setProbing(false);
    setProbe(res.ok ? await res.json() : { ok: false, error: "Probe failed", tools: [], tool_count: 0, latency_ms: 0, auth_required: false, server: {}, protocol: "" });
  };
  const decide = async (c: Connector, value: Connector["approval"]) => {
    const res = await fetch(`/api/pg/v1/connectors/${c.id}/approval`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ approval: value }) });
    if (!res.ok) { toast.error("Could not update the approval"); return; }
    const updated = (await res.json()) as Connector;
    setRows((list) => list.map((x) => (x.id === updated.id ? updated : x)));
    setDetail(updated);
    refreshStats();
    toast.success(`${updated.title} is now ${value}`);
  };
  const sync = async () => {
    setSyncing(true);
    const res = await fetch("/api/pg/v1/connectors/sync", { method: "POST" });
    setSyncing(false);
    if (!res.ok) { toast.error("Registry sync failed"); return; }
    const j = await res.json();
    toast.success(`Registry sync: ${j.added} added, ${j.updated} updated`);
    refreshStats();
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Discover</p>
          <h1 className="text-2xl font-semibold tracking-tight">Connectors</h1>
          <p className="mt-1 text-sm text-muted-foreground">{stats.total.toLocaleString()} MCP servers from the official registry, {stats.by_approval.approved ?? 0} approved by your admins. Every agent can use approved connectors as tools; the playground itself is one of them.</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-brand-emerald/15 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300" data-testid="approved-count">{stats.by_approval.approved ?? 0} approved</span>
          <span className="rounded-full bg-brand-amber/15 px-2.5 py-1 font-medium text-amber-700 dark:text-amber-300">{stats.by_approval.pending ?? 0} pending</span>
          {isAdmin && <Button size="sm" variant="outline" onClick={sync} disabled={syncing} aria-label="Sync registry"><RefreshCw className={cn("size-3.5", syncing && "animate-spin")} /> {syncing ? "Syncing…" : "Sync registry"}</Button>}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <label className="relative">
          <Search className="pointer-events-none absolute left-2 top-2 size-3.5 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search connectors" aria-label="Search connectors" className="h-8 w-64 rounded-lg border bg-card pl-7 pr-2 text-xs outline-none focus-visible:border-brand-violet/60" />
        </label>
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category" className="h-8 rounded-lg border bg-card px-2 text-xs">
          <option value="">All categories</option>
          {stats.categories.map((c) => <option key={c} value={c}>{c} ({stats.by_category[c] ?? 0})</option>)}
        </select>
        <div className="flex gap-1" role="tablist" aria-label="Transport">
          {TRANSPORTS.map((t) => (
            <button key={t || "all"} type="button" role="tab" aria-selected={transport === t} onClick={() => setTransport(t)} className={cn("h-8 rounded-lg border px-2.5 text-xs", transport === t ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground hover:text-foreground")}>{t || "Any transport"}</button>
          ))}
        </div>
        <select value={approval} onChange={(e) => setApproval(e.target.value)} aria-label="Approval" className="h-8 rounded-lg border bg-card px-2 text-xs">
          <option value="">Any approval</option><option value="approved">Approved</option><option value="pending">Pending</option><option value="blocked">Blocked</option>
        </select>
        <span className="ml-auto text-xs text-muted-foreground">{total.toLocaleString()} matching</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="connector-cards">
        {rows.map((c) => (
          <button key={c.id} type="button" onClick={() => open(c)} className="card-hover flex flex-col rounded-2xl border bg-card p-4 text-left" aria-label={c.title}>
            <div className="flex items-center justify-between gap-2">
              <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", APPROVAL_STYLE[c.approval])}>{c.approval}</span>
              <span className="font-mono text-[10px] text-muted-foreground">{c.transport}{c.version ? ` · v${c.version}` : ""}</span>
            </div>
            <h3 className="mt-2 flex items-center gap-1.5 text-sm font-semibold"><Plug className="size-3.5 text-brand-violet-soft" /> {c.title}</h3>
            <p className="mt-1 line-clamp-3 flex-1 text-xs text-muted-foreground">{c.description || "No description in the registry."}</p>
            <p className="mt-2 truncate font-mono text-[10px] text-muted-foreground">{c.id}</p>
          </button>
        ))}
        {rows.length === 0 && <p className="col-span-full rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">No connectors match.</p>}
      </div>

      <Dialog open={detail !== null} onOpenChange={(o) => { if (!o) setDetail(null); }}>
        <DialogContent className="sm:max-w-2xl">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">{detail.title} <span className={cn("rounded-md px-1.5 py-0.5 text-[10px] font-medium", APPROVAL_STYLE[detail.approval])}>{detail.approval}</span></DialogTitle>
                <DialogDescription>{detail.description || "No description in the registry."}</DialogDescription>
              </DialogHeader>
              <dl className="grid grid-cols-[110px_1fr] gap-y-1.5 text-xs">
                <dt className="text-muted-foreground">Registry name</dt><dd className="font-mono">{detail.id}</dd>
                <dt className="text-muted-foreground">Publisher</dt><dd className="font-mono">{detail.publisher}</dd>
                <dt className="text-muted-foreground">Transport</dt><dd>{detail.transport === "remote" ? <span className="font-mono">{detail.remote_url}</span> : <span className="font-mono">{detail.package?.registry} {detail.package?.identifier}</span>}</dd>
                <dt className="text-muted-foreground">Category</dt><dd>{detail.category}</dd>
                {detail.env_vars.length > 0 && <><dt className="text-muted-foreground">Needs</dt><dd className="font-mono">{detail.env_vars.join(", ")}</dd></>}
                {detail.repo_url && <><dt className="text-muted-foreground">Source</dt><dd><a href={detail.repo_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">{detail.repo_url.replace("https://", "")} <ExternalLink className="size-3" /></a></dd></>}
                {detail.approval_note && <><dt className="text-muted-foreground">Admin note</dt><dd>{detail.approval_note}</dd></>}
              </dl>
              <div>
                <div className="flex items-center justify-between"><p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Client configuration</p><CopyButton text={JSON.stringify({ mcpServers: detail.install }, null, 2)} /></div>
                <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-[#0d0d18] p-3 font-mono text-[11px] text-slate-100" data-testid="install-snippet">{JSON.stringify({ mcpServers: detail.install }, null, 2)}</pre>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" onClick={() => runProbe(detail)} disabled={probing} aria-label="Test connection"><Wifi className="size-3.5" /> {probing ? "Connecting…" : "Test connection"}</Button>
                {isAdmin && detail.approval !== "approved" && <Button size="sm" variant="outline" onClick={() => decide(detail, "approved")} aria-label="Approve connector"><ShieldCheck className="size-3.5" /> Approve</Button>}
                {isAdmin && detail.approval !== "blocked" && <Button size="sm" variant="outline" onClick={() => decide(detail, "blocked")} aria-label="Block connector"><ShieldBan className="size-3.5" /> Block</Button>}
              </div>
              {probe && (
                <div className="rounded-xl border p-3 text-xs" data-testid="probe-result">
                  {probe.ok ? (
                    <>
                      <p className="flex items-center gap-1.5 font-medium text-brand-emerald"><Check className="size-3.5" /> Connected to {probe.server.name ?? "server"} {probe.server.version ?? ""} in {probe.latency_ms} ms · {probe.tool_count} tools</p>
                      <ul className="mt-2 max-h-48 space-y-1 overflow-auto">
                        {probe.tools.map((t) => <li key={t.name}><span className="font-mono text-foreground">{t.name}</span> <span className="text-muted-foreground">{t.description}</span></li>)}
                      </ul>
                    </>
                  ) : (
                    <p className="flex items-center gap-1.5 text-brand-rose"><XCircle className="size-3.5" /> {probe.auth_required ? "The server requires authentication (OAuth or an API key). Add the headers in your client configuration." : probe.error}</p>
                  )}
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
