import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { SkillBrowser } from "@/components/catalog/skill-browser";
import type { Skill, SkillStats } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Skills" };
export const dynamic = "force-dynamic";

export default async function SkillsPage() {
  const data = await apiGet<{ skills: Skill[]; stats: SkillStats }>("/v1/skills?limit=300");
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so skills could not load.</div>;
  return <SkillBrowser initial={data.skills} stats={data.stats} />;
}
