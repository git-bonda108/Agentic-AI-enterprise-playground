import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { CloudStudio } from "@/components/faces/cloud-studio";
import type { BlueprintManifest, CatalogEntry, CatalogModel, CloudInfo, SelfHosting } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Cloud platforms" };
export const dynamic = "force-dynamic";

type Clouds = { clouds: CloudInfo[]; modes: Record<string, string>; frameworks: { id: string; name: string }[] };

export default async function CloudsPage({ searchParams }: { searchParams: Promise<{ blueprint?: string; cloud?: string }> }) {
  const { blueprint, cloud } = await searchParams;
  const [clouds, bps, roles, models, selfHosting] = await Promise.all([
    apiGet<Clouds>("/v1/clouds"),
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
    apiGet<{ entries: CatalogEntry[] }>("/v1/catalog?runnable=true&limit=500"),
    apiGet<{ models: (CatalogModel & { allowed: boolean })[] }>("/v1/models"),
    apiGet<SelfHosting>("/v1/clouds/self-hosting"),
  ]);
  if (!clouds || !bps) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable.</div>;
  const seen = new Set(bps.blueprints.map((b) => b.id));
  const options = [...bps.blueprints.map((b) => ({ id: b.id, name: b.name })), ...(roles?.entries ?? []).filter((e) => !seen.has(e.id)).map((e) => ({ id: e.id, name: `${e.name} (${e.family})` }))];
  const initial = options.some((o) => o.id === blueprint) ? blueprint! : options[0].id;
  const modelOptions = [{ id: "smart", name: "Smart routing (gateway only)" }, ...(models?.models ?? []).filter((m) => m.allowed).map((m) => ({ id: m.id, name: `${m.name} (${m.provider})` }))];
  const initialCloud = clouds.clouds.some((c) => c.id === cloud) ? cloud! : clouds.clouds[0].id;
  return <CloudStudio clouds={clouds.clouds} modes={clouds.modes} frameworks={clouds.frameworks} blueprints={options} models={modelOptions} selfHosting={selfHosting} initialBlueprint={initial} initialCloud={initialCloud} />;
}
