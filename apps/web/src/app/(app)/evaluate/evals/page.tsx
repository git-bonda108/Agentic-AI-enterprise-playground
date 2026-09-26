import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { EvalsWorkbench } from "@/components/evals/evals-workbench";
import type { BlueprintManifest, CustomAgent, EvalLibrary, EvalRunRecord, EvalSuiteRecord, RunRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Evals" };
export const dynamic = "force-dynamic";

export default async function EvalsPage({ searchParams }: { searchParams: Promise<{ suite?: string }> }) {
  const { suite } = await searchParams;
  const [suites, library, bps, custom, runs, detail, evalRuns] = await Promise.all([
    apiGet<{ suites: EvalSuiteRecord[] }>("/v1/evals/suites"),
    apiGet<EvalLibrary>("/v1/evals/library"),
    apiGet<{ blueprints: BlueprintManifest[] }>("/v1/blueprints"),
    apiGet<{ agents: CustomAgent[] }>("/v1/custom-agents"),
    apiGet<{ runs: RunRecord[] }>("/v1/runs?limit=50"),
    suite ? apiGet<EvalSuiteRecord>(`/v1/evals/suites/${suite}`) : Promise.resolve(null),
    suite ? apiGet<{ runs: EvalRunRecord[] }>(`/v1/evals/runs?suite_id=${suite}&limit=20`) : Promise.resolve(null),
  ]);
  const initialActive = evalRuns?.runs?.[0] ? await apiGet<EvalRunRecord>(`/v1/evals/runs/${evalRuns.runs[0].id}`) : null;
  if (!suites || !library) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so Evals could not load.</div>;
  const agents = [
    ...(bps?.blueprints ?? []).map((b) => ({ id: b.id, name: b.name, samples: b.samples })),
    ...(custom?.agents ?? []).map((a) => ({ id: a.id, name: `${a.name} (yours)`, samples: (a.starters.length ? a.starters : ["Describe what you do."]).map((s) => ({ name: s.slice(0, 48), input: { task: s } })) })),
  ];
  return <EvalsWorkbench suites={suites.suites} library={library} agents={agents} recentRuns={runs?.runs ?? []} initialDetail={detail} initialRuns={evalRuns?.runs ?? []} initialActive={initialActive} />;
}
