import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { LowcodeStudio } from "@/components/faces/lowcode-studio";
import type { CatalogEntry, LowcodePlatform, LowcodeStudio as Studio } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Low-code studios" };
export const dynamic = "force-dynamic";

export default async function LowcodePage({ searchParams }: { searchParams: Promise<{ blueprint?: string; studio?: string }> }) {
  const { blueprint, studio } = await searchParams;
  const [landscape, catalog] = await Promise.all([
    apiGet<{ platforms: LowcodePlatform[]; studios: Studio[]; playground_mcp_url: string }>("/v1/lowcode/landscape"),
    apiGet<{ entries: CatalogEntry[] }>("/v1/catalog?runnable=true&limit=500"),
  ]);
  if (!landscape || !catalog) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable.</div>;
  const options = catalog.entries
    .filter((e) => e.family === "Domain" || e.family === "Low-code")
    .map((e) => ({ id: e.id, name: e.family === "Domain" ? e.name : `${e.name} (${e.family.toLowerCase()})`, category: e.category }));
  const initial = options.some((o) => o.id === blueprint) ? blueprint! : options[0]?.id ?? "doc-reconciliation";
  const initialStudio = ["langflow", "n8n", "copilot"].includes(studio ?? "") ? studio! : "langflow";
  return <LowcodeStudio blueprints={options} initialBlueprint={initial} initialStudio={initialStudio} studios={landscape.studios} platforms={landscape.platforms} mcpUrl={landscape.playground_mcp_url} />;
}
