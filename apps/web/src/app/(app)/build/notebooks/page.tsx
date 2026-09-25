import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { NotebookWorkbench } from "@/components/notebooks/notebook-workbench";
import type { ConversationSummary, RunRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Notebooks" };
export const dynamic = "force-dynamic";

export default async function NotebooksPage({ searchParams }: { searchParams: Promise<{ source?: string; run?: string; conversation?: string; blueprint?: string }> }) {
  const p = await searchParams;
  const [runs, convs] = await Promise.all([
    apiGet<{ runs: RunRecord[] }>("/v1/runs?limit=6"),
    apiGet<{ conversations: ConversationSummary[] }>("/v1/conversations?limit=6"),
  ]);
  const recent = [
    { label: "Scratch notebook", path: "/v1/notebooks/blank.ipynb" },
    ...(runs?.runs ?? []).map((r) => ({ label: `Run · ${r.blueprint_name}`, path: `/v1/notebooks/run/${r.id}.ipynb` })),
    ...(convs?.conversations ?? []).map((c) => ({ label: `Chat · ${c.title}`, path: `/v1/notebooks/conversation/${c.id}.ipynb` })),
  ];
  const path = p.source ?? (p.run ? `/v1/notebooks/run/${p.run}.ipynb` : p.conversation ? `/v1/notebooks/conversation/${p.conversation}.ipynb` : p.blueprint ? `/v1/notebooks/blueprint/${p.blueprint}.ipynb` : "/v1/notebooks/blank.ipynb");
  const label = recent.find((r) => r.path === path)?.label ?? (p.blueprint ? `Blueprint · ${p.blueprint}` : "Notebook");
  if (p.blueprint && !recent.some((r) => r.path === path)) recent.splice(1, 0, { label, path });
  return <NotebookWorkbench source={{ label, path }} recent={recent} />;
}
