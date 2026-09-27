"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RunStatusPill } from "@/components/runs/run-viewer";
import { formatUsd, type RunRecord } from "@/lib/playground-types";
import { formatWhen } from "@/lib/format";

export function RunsTable({ initial, compact = false }: { initial: RunRecord[]; compact?: boolean }) {
  const [runs, setRuns] = useState(initial);
  useEffect(() => {
    const t = setInterval(async () => {
      const res = await fetch("/api/pg/v1/runs?limit=50");
      if (res.ok) setRuns((await res.json()).runs);
    }, 3000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="overflow-x-auto rounded-2xl border bg-card">
      <table className="w-full text-xs" data-testid="runs-table">
        <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
          <tr><th className="px-3 py-2">Blueprint</th><th className="px-3 py-2">Status</th>{!compact && <th className="px-3 py-2">Person</th>}<th className="px-3 py-2 text-right">Cost</th><th className="px-3 py-2 text-right">Steps</th><th className="px-3 py-2">Started</th><th className="px-3 py-2"></th></tr>
        </thead>
        <tbody>
          {runs.length === 0 && <tr><td colSpan={7} className="px-3 py-8 text-center text-muted-foreground">No runs yet. Start one from the Agent Hub.</td></tr>}
          {runs.map((r) => (
            <tr key={r.id} className={r.status === "waiting_review" ? "border-t bg-brand-pink/5" : "border-t"}>
              <td className="px-3 py-2 font-medium">{r.blueprint_name}</td>
              <td className="px-3 py-2"><RunStatusPill status={r.status} /></td>
              {!compact && <td className="px-3 py-2 text-muted-foreground">{r.user_name ?? r.user_id}</td>}
              <td className="px-3 py-2 text-right font-mono">{formatUsd(r.cost_usd)}</td>
              <td className="px-3 py-2 text-right font-mono">{r.steps.length}</td>
              <td className="px-3 py-2 text-muted-foreground">{formatWhen(r.created_at)}</td>
              <td className="px-3 py-2 text-right"><Link href={`/operate/runs/${r.id}`} className="text-brand-violet-soft hover:underline">{r.status === "waiting_review" ? "Review" : "Open"}</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
