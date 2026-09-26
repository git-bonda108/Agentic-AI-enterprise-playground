import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import { ConnectorBrowser } from "@/components/catalog/connector-browser";
import type { Connector, ConnectorStats, Directory } from "@/lib/playground-types";

export const metadata: Metadata = { title: "MCP Marketplace" };
export const dynamic = "force-dynamic";

export default async function ConnectorsPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q } = await searchParams;
  const [list, stats, featured, session] = await Promise.all([
    apiGet<{ connectors: Connector[]; total: number }>(`/v1/connectors?limit=60${q ? `&q=${encodeURIComponent(q)}` : ""}`),
    apiGet<ConnectorStats>("/v1/connectors/stats"),
    apiGet<{ featured: Connector[]; directories: Directory[] }>("/v1/connectors/featured"),
    auth(),
  ]);
  if (!list || !stats) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the marketplace could not load.</div>;
  return <ConnectorBrowser initial={list.connectors} stats={stats} isAdmin={session?.user?.role === "admin"} featured={featured?.featured ?? []} directories={featured?.directories ?? []} initialQuery={q} />;
}
