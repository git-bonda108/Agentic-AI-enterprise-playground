import Link from "next/link";
import { MODELS } from "@/lib/demo-data";

const TIER_STYLE: Record<string, string> = {
  Frontier: "bg-brand-violet/15 text-violet-700 dark:text-violet-300",
  Premium: "bg-brand-pink/15 text-pink-700 dark:text-pink-300",
  Workhorse: "bg-brand-cyan/15 text-cyan-700 dark:text-cyan-300",
  Economy: "bg-brand-emerald/15 text-emerald-700 dark:text-emerald-300",
};

export function ModelCards() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {MODELS.map((m) => (
        <Link
          key={m.id}
          href="/discover/models"
          className="card-hover group overflow-hidden rounded-2xl border bg-card"
          aria-label={`${m.name} by ${m.provider}`}
        >
          <div className="relative h-24 w-full" style={{ backgroundImage: m.art }}>
            <div className="absolute inset-0 opacity-30 grid-bg" aria-hidden />
            <span className="absolute left-3 top-3 rounded-md bg-black/25 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur">{m.provider}</span>
            {m.isNew && <span className="absolute right-3 top-3 rounded-md bg-white/90 px-1.5 py-0.5 text-[10px] font-semibold text-violet-700">New</span>}
            <span className="absolute bottom-3 right-3 size-8 rounded-full bg-white/20 blur-[1px] transition-transform group-hover:scale-125" aria-hidden />
          </div>
          <div className="p-3.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold">{m.name}</p>
              <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium ${TIER_STYLE[m.tier]}`}>{m.tier}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {m.tags.map((t) => (
                <span key={t} className="rounded-md bg-muted px-1.5 py-0.5 text-[10.5px] text-muted-foreground">{t}</span>
              ))}
            </div>
            <p className="mt-3 font-mono text-[10.5px] text-muted-foreground">
              ${m.input} in · ${m.output} out <span>/ 1M tokens</span>
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}
