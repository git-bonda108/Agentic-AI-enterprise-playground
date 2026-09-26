import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import { ChallengeBoard } from "@/components/community/challenge-board";
import type { BlueprintManifest, ChallengeRecord, CustomAgent, EvalLibrary } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Challenges" };
export const dynamic = "force-dynamic";

export default async function ChallengesPage({ searchParams }: { searchParams: Promise<{ challenge?: string }> }) {
  const { challenge } = await searchParams;
  const [list, bps, custom, library, session] = await Promise.all([
    apiGet<{ challenges: ChallengeRecord[] }>("/v1/community/challenges"),
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
    apiGet<{ agents: CustomAgent[] }>("/v1/custom-agents"),
    apiGet<EvalLibrary>("/v1/evals/library"),
    auth(),
  ]);
  if (!list || !library) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so challenges could not load.</div>;
  const agents = [
    ...(bps?.blueprints ?? []).map((b) => ({ id: b.id, name: b.name, primaryKey: Object.keys(b.samples?.[0]?.input ?? {})[0] ?? "question" })),
    ...(custom?.agents ?? []).map((a) => ({ id: a.id, name: `${a.name} (${a.owner_id === session?.user?.id ? "yours" : "shared"})`, primaryKey: "task" })),
  ];
  const role = session?.user?.role ?? "explorer";
  return <ChallengeBoard initial={list.challenges} agents={agents} rubric={library.rubric} userId={session?.user?.id ?? ""} canRun={role === "admin" || role === "champion"} initialSelected={challenge ?? null} />;
}
