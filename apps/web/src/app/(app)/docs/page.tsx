import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { DocsHub } from "@/components/docs/docs-hub";
import type { DocGuideMeta } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Documentation" };
export const dynamic = "force-dynamic";

export default async function DocsPage() {
  const data = await apiGet<{ sections: string[]; guides: DocGuideMeta[] }>("/v1/docs");
  if (!data) return <div className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center text-sm text-muted-foreground">The API is not reachable.</div>;
  return <DocsHub sections={data.sections} guides={data.guides} />;
}
