import type { Metadata } from "next";
import { Suspense } from "react";
import { apiGet } from "@/lib/api-server";
import { BlueprintGrid } from "@/components/agents/blueprint-grid";
import { RunsTable } from "@/components/runs/runs-table";
import { AgentWizard } from "@/components/agents/agent-wizard";
import { auth } from "@/auth";
import type { BlueprintManifest, Connector, CustomAgent, KnowledgeSpace, RunRecord, Skill } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Agents" };
export const dynamic = "force-dynamic";

export default async function AgentsPage({ searchParams }: { searchParams: Promise<{ blueprint?: string; skill?: string }> }) {
  const { blueprint, skill } = await searchParams;
  const [bps, runs, custom, session, skills, connectors, spaces] = await Promise.all([
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
    apiGet<{ runs: RunRecord[]; waiting_review: number }>("/v1/runs?limit=8"),
    apiGet<{ agents: CustomAgent[] }>("/v1/custom-agents"),
    auth(),
    apiGet<{ skills: Skill[] }>("/v1/skills?limit=400"),
    apiGet<{ connectors: Connector[] }>("/v1/connectors?approval=approved&transport=remote&limit=24"),
    apiGet<{ spaces: KnowledgeSpace[] }>("/v1/knowledge/spaces"),
  ]);
  if (!bps) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the Agent Hub could not load.</div>;
  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Build</p>
        <h1 className="text-2xl font-semibold tracking-tight">Agent Hub</h1>
        <p className="mt-1 text-sm text-muted-foreground">{bps.blueprints.length} runnable blueprints. Every run is checkpointed, metered to you, and pauses for a human where the pattern says so.</p>
      </div>
      <Suspense fallback={null}>
        <BlueprintGrid key={blueprint ?? "none"} blueprints={bps.blueprints} />
      </Suspense>
      <AgentWizard
        initial={custom?.agents ?? []}
        ownerId={session?.user?.id ?? ""}
        presetSkill={skill}
        skills={(skills?.skills ?? []).map((s) => ({ id: s.id, name: s.name, hint: s.category }))}
        connectors={(connectors?.connectors ?? []).map((c) => ({ id: c.id, name: c.title }))}
        spaces={(spaces?.spaces ?? []).map((s) => ({ id: s.id, name: s.name }))}
      />
      <section>
        <div className="mb-3 flex items-end justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Recent runs</h2>
          {runs && runs.waiting_review > 0 && <span className="rounded-full bg-brand-pink/15 px-2.5 py-1 text-xs font-medium text-pink-700 dark:text-pink-300">{runs.waiting_review} waiting for review</span>}
        </div>
        <RunsTable initial={runs?.runs ?? []} compact />
      </section>
    </div>
  );
}
