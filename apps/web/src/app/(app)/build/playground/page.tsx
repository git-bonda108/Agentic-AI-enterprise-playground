import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { Playground } from "@/components/playground/playground";
import type { CatalogModel, ConversationSummary } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Playground" };
export const dynamic = "force-dynamic";

export default async function PlaygroundPage({ searchParams }: { searchParams: Promise<{ model?: string }> }) {
  const params = await searchParams;
  const [catalog, list] = await Promise.all([
    apiGet<{ models: CatalogModel[]; smart_enabled: boolean }>("/v1/models"),
    apiGet<{ conversations: ConversationSummary[] }>("/v1/conversations"),
  ]);
  const models = catalog?.models ?? [];
  if (models.length === 0) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center">
        <h1 className="text-lg font-semibold">Playground</h1>
        <p className="mt-2 text-sm text-muted-foreground">The API is not reachable, so the model catalog could not load. Start it with <code className="rounded bg-muted px-1">npm run api</code> and refresh.</p>
      </div>
    );
  }
  const preferred = ["claude-sonnet-5", "gpt-5.6-terra", "deepseek-v4-flash", "gemini-2.5-flash"];
  const fallback = preferred.find((id) => models.some((m) => m.id === id && m.available)) ?? models.find((m) => m.available)?.id ?? models[0].id;
  const requested = params.model;
  const defaultModel = requested === "smart" && catalog?.smart_enabled ? "smart" : requested && models.some((m) => m.id === requested) ? requested : fallback;
  return <Playground models={models} initialConversations={list?.conversations ?? []} defaultModel={defaultModel} smartEnabled={Boolean(catalog?.smart_enabled)} />;
}
