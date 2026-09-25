import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { RESOURCES } from "@/lib/demo-data";

export function ResourceCards() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {RESOURCES.map((r) => (
        <Link key={r.href} href={r.href} className="card-hover group rounded-2xl border bg-card p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">{r.title}</p>
            <ArrowUpRight className="size-4 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-brand-violet-soft" />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{r.body}</p>
          <p className="mt-3 font-mono text-[10px] text-muted-foreground">batch {r.batch}</p>
        </Link>
      ))}
    </div>
  );
}
