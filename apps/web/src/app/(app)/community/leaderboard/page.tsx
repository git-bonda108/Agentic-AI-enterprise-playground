import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { Leaderboard } from "@/components/community/leaderboard";
import type { CommunityMe, LeaderboardRow } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Leaderboard" };
export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  const [people, departments, me] = await Promise.all([
    apiGet<{ rows: LeaderboardRow[]; points: Record<string, number>; days: number }>("/v1/community/leaderboard?by=user&days=30"),
    apiGet<{ rows: LeaderboardRow[] }>("/v1/community/leaderboard?by=department&days=30"),
    apiGet<CommunityMe>("/v1/community/me"),
  ]);
  if (!people || !me) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so the leaderboard could not load.</div>;
  return <Leaderboard people={people.rows} departments={departments?.rows ?? []} me={me} points={people.points} days={people.days} />;
}
