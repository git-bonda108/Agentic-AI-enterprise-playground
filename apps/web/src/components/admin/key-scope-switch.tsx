"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Scope = "all" | "platform-only";

const OPTIONS: { id: Scope; label: string; blurb: string }[] = [
  { id: "all", label: "Platform keys serve everyone", blurb: "Pilot mode. People can chat, run agents and notebooks on the platform's keys; their own keys take precedence when set." },
  { id: "platform-only", label: "Platform keys serve only the product", blurb: "Bring-your-own-key mode. Platform keys run the judge, canaries and platform agents; people must add their own keys to use models." },
];

export function KeyScopeSwitch({ initial }: { initial: Scope }) {
  const [scope, setScope] = useState<Scope>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const choose = async (next: Scope) => {
    if (next === scope || busy) return;
    setBusy(true); setError(null);
    const res = await fetch("/api/pg/v1/keys/admin/scope", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ scope: next }) });
    setBusy(false);
    if (!res.ok) { setError("Could not change the scope"); return; }
    setScope(next);
  };

  return (
    <section className="rounded-2xl border bg-card p-4 text-xs" aria-label="Platform key scope" data-testid="key-scope">
      <h2 className="text-sm font-semibold">Who the platform keys serve</h2>
      <p className="mt-1 text-muted-foreground">Platform keys live in the API environment and are never shown. Personal keys are stored encrypted and used first.</p>
      <div className="mt-3 grid gap-2">
        {OPTIONS.map((o) => (
          <button
            key={o.id} type="button" aria-pressed={scope === o.id} disabled={busy} onClick={() => void choose(o.id)}
            className={cn("rounded-xl border p-3 text-left transition-colors", scope === o.id ? "border-brand-violet/60 bg-brand-violet/10" : "hover:border-brand-violet/30")}
          >
            <span className="flex items-center gap-2 text-sm font-medium">{o.label}{busy && scope !== o.id && <Loader2 className="size-3 animate-spin" />}</span>
            <span className="mt-0.5 block text-muted-foreground">{o.blurb}</span>
          </button>
        ))}
      </div>
      {error && <p className="mt-2 text-brand-rose">{error}</p>}
    </section>
  );
}
