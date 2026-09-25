import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { CatalogBrowser } from "@/components/catalog/catalog-browser";
import type { CatalogEntry, CatalogStats } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Blueprints" };
export const dynamic = "force-dynamic";

export default async function BlueprintsPage() {
  const data = await apiGet<{ entries: CatalogEntry[]; families: string[]; stats: CatalogStats }>("/v1/catalog");
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the catalog could not load.</div>;
  return <CatalogBrowser initial={data.entries} families={data.families} stats={data.stats} />;
}
