import type { Metadata } from "next";
import Link from "next/link";
import { auth } from "@/auth";
import { apiGet } from "@/lib/api-server";
import type { UsageSummary } from "@/lib/playground-types";
import { Greeting } from "@/components/home/greeting";
import { StatCards } from "@/components/home/stat-cards";
import { HoursTiles } from "@/components/home/hours-tiles";
import { GatewayHero } from "@/components/home/gateway-hero";
import { ModelCards } from "@/components/home/model-cards";
import { BlueprintCards } from "@/components/home/blueprint-cards";
import { ResourceCards } from "@/components/home/resource-cards";

export const metadata: Metadata = { title: "Console" };
export const dynamic = "force-dynamic";

function SectionHeading({ title, href, action }: { title: string; href: string; action: string }) {
  return (
    <div className="mb-3 flex items-end justify-between">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <Link href={href} className="text-xs font-medium text-brand-violet-soft hover:underline">{action}</Link>
    </div>
  );
}

export default async function HomePage() {
  const [session, summary] = await Promise.all([auth(), apiGet<UsageSummary>("/v1/usage/summary?days=7")]);
  const name = session?.user?.name ?? "there";
  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Greeting name={name} />
          <p className="mt-1 text-sm text-muted-foreground">{summary ? "Live from the usage ledger. Every playground message lands here within a second." : "The API is offline, so these numbers are seeded. Start it to see the live ledger."}</p>
        </div>
        <span className="rounded-full border bg-card px-3 py-1 text-xs text-muted-foreground">{session?.user?.department} · {session?.user?.role}</span>
      </div>

      <StatCards summary={summary} />
      <HoursTiles hours={summary?.hours} />
      <GatewayHero />

      <section>
        <SectionHeading title="Models" href="/discover/models" action="Compare models" />
        <ModelCards />
      </section>

      <section>
        <SectionHeading title="Jumpstart a blueprint" href="/discover/blueprints" action="All blueprints" />
        <BlueprintCards />
      </section>

      <section>
        <SectionHeading title="Resources" href="/build/playground" action="Go to Build" />
        <ResourceCards />
      </section>
    </div>
  );
}
