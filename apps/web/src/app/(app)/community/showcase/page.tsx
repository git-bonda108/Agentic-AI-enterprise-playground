import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import { ShowcaseBoard } from "@/components/community/showcase-board";
import type { CustomAgent, RunRecord, ShowcaseItemRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Showcase" };
export const dynamic = "force-dynamic";

export default async function ShowcasePage() {
  const [list, runs, agents, session] = await Promise.all([
    apiGet<{ items: ShowcaseItemRecord[]; tags: Record<string, number> }>("/v1/community/showcase"),
    apiGet<{ runs: RunRecord[] }>("/v1/runs?limit=50"),
    apiGet<{ agents: CustomAgent[] }>("/v1/custom-agents"),
    auth(),
  ]);
  if (!list) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the showcase could not load.</div>;
  const me = session?.user?.id ?? "";
  return <ShowcaseBoard initial={list.items} tags={list.tags} myRuns={(runs?.runs ?? []).filter((r) => r.user_id === me && r.status === "completed")} myAgents={(agents?.agents ?? []).filter((a) => a.owner_id === me)} userId={me} isAdmin={session?.user?.role === "admin"} />;
}
