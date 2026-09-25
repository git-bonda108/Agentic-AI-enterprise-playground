import type { Metadata } from "next";
import path from "node:path";
import { apiGet } from "@/lib/api-server";
import { KnowledgeWorkbench } from "@/components/knowledge/knowledge-workbench";
import type { DatasetInfo, EmbeddingModel, KnowledgeDocument, KnowledgeSpace } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Knowledge" };
export const dynamic = "force-dynamic";

export default async function KnowledgePage({ searchParams }: { searchParams: Promise<{ space?: string }> }) {
  const { space } = await searchParams;
  const [spaces, models, data, detail] = await Promise.all([
    apiGet<{ spaces: KnowledgeSpace[] }>("/v1/knowledge/spaces"),
    apiGet<{ models: EmbeddingModel[] }>("/v1/knowledge/embedding-models"),
    apiGet<{ datasets: DatasetInfo[] }>("/v1/data"),
    space ? apiGet<KnowledgeSpace & { documents: KnowledgeDocument[]; can_edit: boolean }>(`/v1/knowledge/spaces/${space}`) : Promise.resolve(null),
  ]);
  if (!spaces || !models) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so Knowledge could not load.</div>;
  // The playground's own API is the default repository to map: a demo that needs nothing external.
  const repoRoot = path.resolve(process.cwd(), "..", "api", "app");
  return <KnowledgeWorkbench spaces={spaces.spaces} models={models.models} datasets={data?.datasets ?? []} initialDetail={detail} repoRoot={repoRoot} />;
}
