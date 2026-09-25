import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import type { DatasetInfo } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Data" };
export const dynamic = "force-dynamic";

export default async function DataPage() {
  const data = await apiGet<{ datasets: DatasetInfo[] }>("/v1/data");
  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Build</p>
      <h1 className="text-2xl font-semibold tracking-tight">Data</h1>
      <p className="mt-1 text-sm text-muted-foreground">Mock datasets every blueprint can run against safely. Synthetic, generated deterministically, modeled on public sets.</p>
      <div className="mt-5 grid gap-4 md:grid-cols-2" data-testid="datasets">
        {(data?.datasets ?? []).map((d) => (
          <section key={d.id} className="rounded-2xl border bg-card p-4" aria-label={d.title}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">{d.title}</h2>
              <span className="font-mono text-[11px] text-muted-foreground">{d.rows} rows · {d.file}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{d.source}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">Used by: {d.used_by.join(", ")}</p>
            <pre className="mt-3 max-h-40 overflow-auto rounded-lg bg-muted p-2 font-mono text-[10.5px] text-muted-foreground">{JSON.stringify(d.preview.slice(0, 3), null, 1)}</pre>
          </section>
        ))}
        {!data && <p className="text-sm text-muted-foreground">The API is not reachable.</p>}
      </div>
    </div>
  );
}
