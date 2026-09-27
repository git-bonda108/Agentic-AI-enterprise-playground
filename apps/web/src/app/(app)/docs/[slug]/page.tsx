import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { apiGet } from "@/lib/api-server";
import { DocView } from "@/components/docs/doc-view";
import type { DocGuide } from "@/lib/playground-types";

type Params = Promise<{ slug: string }>;
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const guide = await apiGet<DocGuide>(`/v1/docs/${encodeURIComponent(slug)}`);
  return { title: guide ? guide.title : "Documentation" };
}

export default async function DocPage({ params }: { params: Params }) {
  const { slug } = await params;
  const guide = await apiGet<DocGuide>(`/v1/docs/${encodeURIComponent(slug)}`);
  if (!guide) notFound();
  return <DocView guide={guide} />;
}
