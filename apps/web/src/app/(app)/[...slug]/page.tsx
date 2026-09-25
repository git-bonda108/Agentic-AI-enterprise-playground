import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { findNavItem } from "@/lib/nav";
import { SectionPage } from "@/components/shell/section-page";

type Params = Promise<{ slug: string[] }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const match = findNavItem(`/${slug.join("/")}`);
  return { title: match ? match.item.title : "Not found" };
}

export default async function Page({ params }: { params: Params }) {
  const { slug } = await params;
  const match = findNavItem(`/${slug.join("/")}`);
  if (!match) notFound();
  return <SectionPage section={match.section} item={match.item} />;
}
