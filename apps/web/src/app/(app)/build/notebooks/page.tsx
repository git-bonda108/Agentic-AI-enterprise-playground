import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { NotebookWorkbench, type ComputeOption, type GalleryItem } from "@/components/notebooks/notebook-workbench";
import type { ConversationSummary, RunRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Notebooks" };
export const dynamic = "force-dynamic";

export default async function NotebooksPage({ searchParams }: { searchParams: Promise<{ source?: string; run?: string; conversation?: string; blueprint?: string }> }) {
  const p = await searchParams;
  const path = p.source ?? (p.run && p.run !== "sandbox" ? `/v1/notebooks/run/${p.run}.ipynb` : p.conversation ? `/v1/notebooks/conversation/${p.conversation}.ipynb` : p.blueprint ? `/v1/notebooks/blueprint/${p.blueprint}.ipynb` : null);
  const [runs, convs, galleryRes, computeRes] = await Promise.all([
    apiGet<{ runs: RunRecord[] }>("/v1/runs?limit=6"),
    apiGet<{ conversations: ConversationSummary[] }>("/v1/conversations?limit=6"),
    apiGet<{ notebooks: GalleryItem[] }>("/v1/notebooks/gallery"),
    path ? apiGet<{ options: ComputeOption[] }>(`/v1/notebooks/compute?path=${encodeURIComponent(path)}`) : Promise.resolve(null),
  ]);
  const gallery = galleryRes?.notebooks ?? [];
  const recent = [
    { label: "Scratch notebook", path: "/v1/notebooks/blank.ipynb" },
    ...(runs?.runs ?? []).map((r) => ({ label: `Run · ${r.blueprint_name}`, path: `/v1/notebooks/run/${r.id}.ipynb` })),
    ...(convs?.conversations ?? []).map((c) => ({ label: `Chat · ${c.title}`, path: `/v1/notebooks/conversation/${c.id}.ipynb` })),
  ];
  const chosen = path ?? "/v1/notebooks/blank.ipynb";
  const fromGallery = gallery.find((g) => g.path === chosen);
  const label = recent.find((r) => r.path === chosen)?.label ?? fromGallery?.title ?? (p.blueprint ? `Blueprint · ${p.blueprint}` : "Notebook");
  if (path && !recent.some((r) => r.path === chosen)) recent.splice(1, 0, { label, path: chosen });
  // Keyed by notebook and mode so client-side navigation from the gallery remounts the workbench (tab state resets).
  return <NotebookWorkbench key={`${chosen}:${p.run === "sandbox"}`} source={{ label, path: chosen }} recent={recent} gallery={gallery} compute={computeRes?.options ?? []} showGallery={!path} autorun={p.run === "sandbox"} />;
}
