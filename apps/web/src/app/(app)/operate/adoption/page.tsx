import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import { AdoptionDashboard } from "@/components/adoption/adoption-dashboard";
import type { AdoptionSummary } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Adoption" };
export const dynamic = "force-dynamic";

export default async function AdoptionPage() {
  const [data, session] = await Promise.all([apiGet<AdoptionSummary>("/v1/adoption/summary?days=30"), auth()]);
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so adoption analytics could not load.</div>;
  return <AdoptionDashboard initial={data} isAdmin={session?.user?.role === "admin"} />;
}
