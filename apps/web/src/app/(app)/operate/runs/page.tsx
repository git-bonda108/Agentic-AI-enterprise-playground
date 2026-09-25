import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { RunsTable } from "@/components/runs/runs-table";
import type { RunRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Runs" };
export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const data = await apiGet<{ runs: RunRecord[]; waiting_review: number }>("/v1/runs?limit=50");
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Operate</p>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="mt-1 text-sm text-muted-foreground">Every agent run with its state, cost and review inbox. Refreshes every few seconds.</p>
        </div>
        {data && data.waiting_review > 0 && <span className="rounded-full bg-brand-pink/15 px-2.5 py-1 text-xs font-medium text-pink-700 dark:text-pink-300">{data.waiting_review} waiting for your review</span>}
      </div>
      <div className="mt-5"><RunsTable initial={data?.runs ?? []} /></div>
    </div>
  );
}
