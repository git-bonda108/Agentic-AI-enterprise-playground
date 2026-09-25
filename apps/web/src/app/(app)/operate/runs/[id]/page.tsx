import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { apiGet } from "@/lib/api-server";
import { RunViewer } from "@/components/runs/run-viewer";
import type { BlueprintManifest, RunRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Run" };
export const dynamic = "force-dynamic";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await apiGet<RunRecord>(`/v1/runs/${id}`);
  if (!run) notFound();
  const manifest = await apiGet<BlueprintManifest>(`/v1/blueprints/${run.blueprint_id}`);
  if (!manifest) notFound();
  return <RunViewer initial={run} manifest={manifest} />;
}
