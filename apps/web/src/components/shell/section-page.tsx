import { type NavItem, type NavSection, CURRENT_BATCH } from "@/lib/nav";
import { Skeleton } from "@/components/ui/skeleton";

const BATCH_TITLES: Record<number, string> = {
  0: "Skeleton and design system",
  1: "Gateway, playground, ledger",
  2: "Model catalog, router, cost cockpit, admin",
  3: "Blueprint runtime and first six",
  4: "Catalog import and Discover",
  5: "Notebook, flavors, cloud deploy, no-code",
  6: "Connectors, knowledge, skills",
  7: "Evaluate, canary, hardening",
  8: "Community, engagement, analytics",
  9: "Ship",
};

export function SectionPage({ section, item }: { section: NavSection; item: NavItem }) {
  const live = item.batch <= CURRENT_BATCH;
  return (
    <div className="mx-auto max-w-6xl">
      <div className="relative overflow-hidden rounded-2xl border bg-card p-8">
        <div className="absolute -right-24 -top-24 size-72 rounded-full bg-[radial-gradient(circle,color-mix(in_oklch,var(--brand-violet)_28%,transparent),transparent_65%)] blur-2xl" aria-hidden />
        <div className="relative flex items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-xl border bg-background text-brand-violet-soft">
            <item.icon className="size-6" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{section.title}</p>
            <h1 className="mt-0.5 text-2xl font-semibold tracking-tight">{item.title}</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{item.blurb}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className={live ? "rounded-full bg-brand-emerald/15 px-2.5 py-1 text-xs font-medium text-brand-emerald" : "rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"}>
                {live ? "Live" : `Lands in batch ${item.batch}: ${BATCH_TITLES[item.batch]}`}
              </span>
            </div>
          </div>
        </div>
      </div>

      {!live && (
        <div className="mt-6 grid gap-4 md:grid-cols-3" aria-label="Layout preview">
          <div className="rounded-2xl border bg-card p-5 md:col-span-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="mt-3 h-40 w-full rounded-xl" />
            <div className="mt-3 grid grid-cols-3 gap-3">
              <Skeleton className="h-16 rounded-xl" />
              <Skeleton className="h-16 rounded-xl" />
              <Skeleton className="h-16 rounded-xl" />
            </div>
          </div>
          <div className="rounded-2xl border bg-card p-5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="mt-3 h-8 w-full" />
            <Skeleton className="mt-2 h-8 w-full" />
            <Skeleton className="mt-2 h-8 w-5/6" />
            <Skeleton className="mt-6 h-24 w-full rounded-xl" />
          </div>
        </div>
      )}
    </div>
  );
}
