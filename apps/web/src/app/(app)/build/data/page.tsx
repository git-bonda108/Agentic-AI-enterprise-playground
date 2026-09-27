import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { DatasetsBrowser } from "@/components/data/datasets-browser";
import type { GalleryItem } from "@/components/notebooks/notebook-workbench";
import type { BlueprintManifest, DataSource, DatasetInfo } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Datasets" };
export const dynamic = "force-dynamic";

export default async function DataPage() {
  const [data, sources, gallery, bps] = await Promise.all([
    apiGet<{ datasets: DatasetInfo[] }>("/v1/data"),
    apiGet<{ sources: DataSource[] }>("/v1/data/sources"),
    apiGet<{ notebooks: GalleryItem[] }>("/v1/notebooks/gallery"),
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
  ]);
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable.</div>;
  const notebookPaths = Object.fromEntries((gallery?.notebooks ?? []).map((n) => [n.slug, n.path]));
  const blueprintNames = Object.fromEntries((bps?.blueprints ?? []).map((b) => [b.id, b.name]));
  return <DatasetsBrowser datasets={data.datasets} sources={sources?.sources ?? []} notebookPaths={notebookPaths} blueprintNames={blueprintNames} />;
}
