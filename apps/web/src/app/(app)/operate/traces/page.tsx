import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { TracesView, type TraceItem } from "@/components/runs/traces-view";

export const metadata: Metadata = { title: "Traces" };
export const dynamic = "force-dynamic";

export default async function TracesPage() {
  const data = await apiGet<{ traces: TraceItem[]; days: number; scope: string }>("/v1/traces?days=7");
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so traces could not load.</div>;
  return <TracesView initial={data.traces} scope={data.scope} days={data.days} />;
}
