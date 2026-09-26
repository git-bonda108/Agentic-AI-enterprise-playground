import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { RepoBrowser } from "@/components/catalog/repo-browser";
import type { Repo, RepoCategory } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Popular Git repos" };
export const dynamic = "force-dynamic";

export default async function ReposPage() {
  const data = await apiGet<{ repos: Repo[]; total: number; generated_at: string | null; categories: RepoCategory[]; stars_total: number }>("/v1/repos");
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable, so repositories could not load.</div>;
  return <RepoBrowser initial={data.repos} categories={data.categories} generatedAt={data.generated_at} starsTotal={data.stars_total} />;
}
