import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import { ConnectorBrowser } from "@/components/catalog/connector-browser";
import type { Connector, ConnectorStats } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Connectors" };
export const dynamic = "force-dynamic";

export default async function ConnectorsPage() {
  const [list, stats, session] = await Promise.all([
    apiGet<{ connectors: Connector[]; total: number }>("/v1/connectors?limit=60"),
    apiGet<ConnectorStats>("/v1/connectors/stats"),
    auth(),
  ]);
  if (!list || !stats) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so connectors could not load.</div>;
  return <ConnectorBrowser initial={list.connectors} stats={stats} isAdmin={session?.user?.role === "admin"} />;
}
