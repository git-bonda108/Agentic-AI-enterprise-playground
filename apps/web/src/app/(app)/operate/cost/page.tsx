import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { CostCockpit } from "@/components/cost/cost-cockpit";
import type { Breakdown } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Cost" };
export const dynamic = "force-dynamic";

export default async function CostPage() {
  const [byModel, byDay] = await Promise.all([
    apiGet<Breakdown>("/v1/usage/breakdown?days=30&by=model"),
    apiGet<Breakdown>("/v1/usage/breakdown?days=30&by=day"),
  ]);
  if (!byModel || !byDay) {
    return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the cost cockpit could not load.</div>;
  }
  return <CostCockpit initial={byModel} initialDays={byDay} />;
}
