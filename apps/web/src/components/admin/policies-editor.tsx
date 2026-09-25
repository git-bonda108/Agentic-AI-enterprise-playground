"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ROLE_LABEL, type Role } from "@/lib/users";
import { cn } from "@/lib/utils";

export type PolicyRow = { role: Role; allowed_tiers: string[]; allowed_providers: string[]; max_tokens: number; smart_enabled: boolean };

export function PoliciesEditor({ initial, tiers, providers }: { initial: PolicyRow[]; tiers: string[]; providers: string[] }) {
  const [rows, setRows] = useState(initial);
  const update = (role: Role, patch: Partial<PolicyRow>) => setRows((rs) => rs.map((r) => (r.role === role ? { ...r, ...patch } : r)));
  const save = async (row: PolicyRow) => {
    const res = await fetch(`/api/pg/v1/admin/policies/${row.role}`, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ allowed_tiers: row.allowed_tiers, allowed_providers: row.allowed_providers, max_tokens: row.max_tokens, smart_enabled: row.smart_enabled }) });
    if (res.ok) toast.success(`${ROLE_LABEL[row.role]} policy saved`); else toast.error("Could not save policy");
  };
  const reset = async () => {
    const res = await fetch("/api/pg/v1/admin/policies/reset", { method: "POST" });
    if (res.ok) { const data = await (await fetch("/api/pg/v1/admin/policies")).json(); setRows(data.policies); toast.success("Policies reset to defaults"); }
  };
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {rows.map((row) => (
          <section key={row.role} className="rounded-2xl border bg-card p-4" aria-label={`${ROLE_LABEL[row.role]} policy`}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">{ROLE_LABEL[row.role]}</h2>
              <Button size="sm" onClick={() => save(row)} aria-label={`Save ${ROLE_LABEL[row.role]} policy`}>Save</Button>
            </div>
            <p className="mt-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Allowed tiers</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {tiers.map((t) => {
                const on = row.allowed_tiers.includes(t);
                return (
                  <button key={t} type="button" aria-pressed={on} onClick={() => update(row.role, { allowed_tiers: on ? row.allowed_tiers.filter((x) => x !== t) : [...row.allowed_tiers, t] })} className={cn("h-7 rounded-md border px-2 text-xs", on ? "border-brand-violet/60 bg-secondary text-secondary-foreground" : "text-muted-foreground")}>{t}</button>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Providers (none selected means all)</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {providers.map((p) => {
                const on = row.allowed_providers.includes(p);
                return (
                  <button key={p} type="button" aria-pressed={on} onClick={() => update(row.role, { allowed_providers: on ? row.allowed_providers.filter((x) => x !== p) : [...row.allowed_providers, p] })} className={cn("h-7 rounded-md border px-2 text-xs", on ? "border-brand-cyan/60 bg-brand-cyan/10" : "text-muted-foreground")}>{p}</button>
                );
              })}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs">
              <label className="flex items-center gap-2">Max output tokens
                <input type="number" min={256} max={128000} step={256} value={row.max_tokens} onChange={(e) => update(row.role, { max_tokens: Number(e.target.value) })} aria-label={`Max tokens for ${ROLE_LABEL[row.role]}`} className="h-8 w-28 rounded-lg border bg-background px-2 font-mono" />
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={row.smart_enabled} onChange={(e) => update(row.role, { smart_enabled: e.target.checked })} className="accent-[var(--brand-violet)]" aria-label={`Smart routing for ${ROLE_LABEL[row.role]}`} /> Smart routing
              </label>
            </div>
          </section>
        ))}
      </div>
      <Button variant="outline" size="sm" onClick={reset}>Reset to defaults</Button>
    </div>
  );
}
