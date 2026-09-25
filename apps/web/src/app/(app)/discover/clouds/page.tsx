import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { CloudStudio } from "@/components/faces/cloud-studio";
import type { BlueprintManifest, CatalogEntry, CloudInfo } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Clouds" };
export const dynamic = "force-dynamic";

export default async function CloudsPage({ searchParams }: { searchParams: Promise<{ blueprint?: string }> }) {
  const { blueprint } = await searchParams;
  const [clouds, bps, roles] = await Promise.all([
    apiGet<{ clouds: CloudInfo[] }>("/v1/clouds"),
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
    apiGet<{ entries: CatalogEntry[] }>("/v1/catalog?runnable=true&limit=500"),
  ]);
  if (!clouds || !bps) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable.</div>;
  const seen = new Set(bps.blueprints.map((b) => b.id));
  const options = [...bps.blueprints.map((b) => ({ id: b.id, name: b.name })), ...(roles?.entries ?? []).filter((e) => !seen.has(e.id)).map((e) => ({ id: e.id, name: `${e.name} (${e.family})` }))];
  const initial = options.some((o) => o.id === blueprint) ? blueprint! : options[0].id;
  return <CloudStudio clouds={clouds.clouds} blueprints={options} initialBlueprint={initial} />;
}
