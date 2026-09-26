import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import { CanaryBoard } from "@/components/evals/canary-board";
import type { AlertItem, CanaryBoardRow, EvalRunRecord } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Canary" };
export const dynamic = "force-dynamic";

export default async function CanaryPage() {
  const [board, alerts, session] = await Promise.all([apiGet<{ canaries: CanaryBoardRow[] }>("/v1/evals/canary"), apiGet<{ alerts: AlertItem[] }>("/v1/alerts"), auth()]);
  if (!board) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the canary board could not load.</div>;
  const history: Record<string, EvalRunRecord[]> = {};
  await Promise.all(board.canaries.map(async (c) => {
    const r = await apiGet<{ runs: EvalRunRecord[] }>(`/v1/evals/runs?suite_id=${c.suite_id}&kind=canary&limit=30`);
    history[c.suite_id] = (r?.runs ?? []).slice().reverse();
  }));
  return <CanaryBoard rows={board.canaries} history={history} alerts={alerts?.alerts ?? []} isAdmin={session?.user?.role === "admin"} />;
}
