import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { FrameworkStudio } from "@/components/faces/framework-studio";
import type { BlueprintManifest, CatalogEntry, FrameworkInfo } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Frameworks" };
export const dynamic = "force-dynamic";

export default async function FrameworksPage({ searchParams }: { searchParams: Promise<{ blueprint?: string }> }) {
  const { blueprint } = await searchParams;
  const [fw, bps, lowcode] = await Promise.all([
    apiGet<{ frameworks: FrameworkInfo[] }>("/v1/frameworks"),
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
    apiGet<{ entries: CatalogEntry[] }>("/v1/catalog?family=Low-code&runnable=true"),
  ]);
  if (!fw || !bps) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable.</div>;
  const options = [...bps.blueprints.map((b) => ({ id: b.id, name: b.name })), ...(lowcode?.entries ?? []).map((e) => ({ id: e.id, name: `${e.name} (low-code)` }))];
  const initial = options.some((o) => o.id === blueprint) ? blueprint! : options[0].id;
  return <FrameworkStudio frameworks={fw.frameworks} blueprints={options} initialBlueprint={initial} />;
}
