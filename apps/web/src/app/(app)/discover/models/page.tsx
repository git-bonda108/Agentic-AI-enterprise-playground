import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { ModelCatalog } from "@/components/catalog/model-catalog";
import type { CatalogModel } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Models" };
export const dynamic = "force-dynamic";

export default async function ModelsPage() {
  const data = await apiGet<{ models: (CatalogModel & { allowed: boolean })[]; smart_enabled: boolean }>("/v1/models");
  if (!data) {
    return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the catalog could not load.</div>;
  }
  return <ModelCatalog models={data.models} smartEnabled={data.smart_enabled} />;
}
