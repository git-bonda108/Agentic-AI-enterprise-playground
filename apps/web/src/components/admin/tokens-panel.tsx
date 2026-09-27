"use client";

import { useState } from "react";
import { KeyRound, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/playground/copy-button";
import type { ApiTokenInfo } from "@/lib/playground-types";
import { formatWhen } from "@/lib/format";

export function TokensPanel({ initial, mcpUrl }: { initial: ApiTokenInfo[]; mcpUrl: string }) {
  const [tokens, setTokens] = useState(initial);
  const [name, setName] = useState("");
  const [fresh, setFresh] = useState<{ token: string; config: unknown } | null>(null);

  const create = async () => {
    if (name.trim().length < 2) { toast.error("Name the token after the client that will use it"); return; }
    const res = await fetch("/api/pg/v1/tokens", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name }) });
    if (!res.ok) { toast.error("Could not create the token"); return; }
    const j = await res.json();
    setTokens((t) => [{ id: j.id, name: j.name, prefix: j.prefix, created_at: j.created_at, last_used_at: null }, ...t]);
    setFresh({ token: j.token, config: j.client_config });
    setName("");
  };
  const revoke = async (id: string) => {
    const res = await fetch(`/api/pg/v1/tokens/${id}`, { method: "DELETE" });
    if (res.ok) setTokens((t) => t.filter((x) => x.id !== id));
  };

  return (
    <section className="rounded-2xl border bg-card p-4 text-xs" aria-label="MCP access" data-testid="tokens-panel">
      <h2 className="flex items-center gap-1.5 text-sm font-semibold"><KeyRound className="size-4 text-brand-violet-soft" /> Connect Claude Desktop, Cursor or VS Code</h2>
      <p className="mt-1 text-muted-foreground">The playground is an MCP server at <span className="font-mono">{mcpUrl}</span>. A personal token lets an external client list models, run blueprints and search Knowledge Spaces as you, under your policy and budget.</p>
      <div className="mt-3 flex gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} aria-label="Token name" placeholder="Claude Desktop on my laptop" className="h-8 flex-1 rounded-lg border bg-background px-2 text-xs" />
        <Button size="sm" onClick={create} aria-label="Create token"><Plus className="size-3.5" /> Create token</Button>
      </div>
      {fresh && (
        <div className="mt-3 rounded-xl border border-brand-violet/40 bg-brand-violet/5 p-3" data-testid="fresh-token">
          <p className="font-medium">Copy this now. It is shown once and stored only as a hash.</p>
          <div className="mt-1 flex items-center gap-2"><code className="flex-1 truncate rounded bg-background px-2 py-1 font-mono">{fresh.token}</code><CopyButton text={fresh.token} label="Copy token" /></div>
          <p className="mt-2 text-muted-foreground">Client configuration (paste into the MCP settings of your client):</p>
          <div className="relative mt-1"><pre className="overflow-auto rounded-lg bg-[#0d0d18] p-3 font-mono text-[11px] text-slate-100">{JSON.stringify(fresh.config, null, 2)}</pre><div className="absolute right-2 top-2"><CopyButton text={JSON.stringify(fresh.config, null, 2)} /></div></div>
        </div>
      )}
      <ul className="mt-3 divide-y" data-testid="token-list">
        {tokens.map((t) => (
          <li key={t.id} className="flex items-center justify-between py-1.5">
            <span><span className="font-medium">{t.name}</span> <span className="font-mono text-muted-foreground">{t.prefix}…</span></span>
            <span className="flex items-center gap-3 text-muted-foreground">{t.last_used_at ? `used ${formatWhen(t.last_used_at)}` : "never used"}<button type="button" onClick={() => revoke(t.id)} aria-label={`Revoke ${t.name}`} className="rounded p-1 hover:bg-muted hover:text-destructive"><Trash2 className="size-3.5" /></button></span>
          </li>
        ))}
        {tokens.length === 0 && <li className="py-2 text-muted-foreground">No tokens yet.</li>}
      </ul>
    </section>
  );
}
