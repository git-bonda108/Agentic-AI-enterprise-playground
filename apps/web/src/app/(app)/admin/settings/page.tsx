import type { Metadata } from "next";
import { Check, ExternalLink, KeyRound } from "lucide-react";
import { apiGet } from "@/lib/api-server";
import { AdminShell } from "@/components/admin/admin-shell";
import { TokensPanel } from "@/components/admin/tokens-panel";
import { KeyScopeSwitch } from "@/components/admin/key-scope-switch";
import type { ApiTokenInfo } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Settings" };
export const dynamic = "force-dynamic";

type SettingsData = {
  environment: string; fake_llm: boolean; database: string; org_credits_usd: number; key_scope: "all" | "platform-only"; key_encryption: string;
  providers: { provider: string; env_key: string; configured: boolean; models: number; docs_url: string; key_page: string; pricing: string }[];
};

export default async function AdminSettingsPage() {
  const [data, tokens] = await Promise.all([apiGet<SettingsData>("/v1/admin/settings"), apiGet<{ tokens: ApiTokenInfo[]; mcp_url: string }>("/v1/tokens")]);
  return (
    <AdminShell title="Settings" blurb="Platform provider keys, who they serve, environment and runtime. Platform keys are read from the API's environment and never shown; personal keys are encrypted at rest." active="/admin/settings">
      {!data ? <p className="text-sm text-muted-foreground">API unreachable.</p> : (
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-2xl border bg-card" aria-label="Providers">
            <table className="w-full text-xs" data-testid="providers-table">
              <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr><th className="px-3 py-2">Provider</th><th className="px-3 py-2">Environment key</th><th className="px-3 py-2">Models</th><th className="px-3 py-2">Platform key</th><th className="px-3 py-2"></th></tr>
              </thead>
              <tbody>
                {data.providers.map((p) => (
                  <tr key={p.provider} className="border-t">
                    <td className="px-3 py-2 font-medium">{p.provider}</td>
                    <td className="px-3 py-2 font-mono text-muted-foreground">{p.env_key}</td>
                    <td className="px-3 py-2">{p.models}</td>
                    <td className="px-3 py-2">{p.configured ? <span className="inline-flex items-center gap-1 text-brand-emerald"><Check className="size-3" /> Configured</span> : <span className="inline-flex items-center gap-1 text-muted-foreground"><KeyRound className="size-3" /> Not set</span>}</td>
                    <td className="space-x-3 px-3 py-2 text-right whitespace-nowrap">
                      <a href={p.key_page} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-violet-soft hover:underline">Get a key <ExternalLink className="size-3" /></a>
                      <a href={p.docs_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">Docs <ExternalLink className="size-3" /></a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section className="rounded-2xl border bg-card p-4 text-xs" aria-label="Runtime">
            <h2 className="text-sm font-semibold">Runtime</h2>
            <dl className="mt-2 grid grid-cols-2 gap-y-2">
              <dt className="text-muted-foreground">Environment</dt><dd className="font-mono">{data.environment}</dd>
              <dt className="text-muted-foreground">Database</dt><dd className="font-mono">{data.database}</dd>
              <dt className="text-muted-foreground">Provider mode</dt><dd className="font-mono">{data.fake_llm ? "fake (offline)" : "live"}</dd>
              <dt className="text-muted-foreground">Org credits</dt><dd className="font-mono">${data.org_credits_usd.toLocaleString()}</dd>
              <dt className="text-muted-foreground">Key encryption</dt><dd className="font-mono">{data.key_encryption}</dd>
            </dl>
            <p className="mt-4 text-muted-foreground">Identity comes from Entra ID when the AUTH_MICROSOFT_ENTRA_ID variables are set; seeded users are for development only.</p>
          </section>
          <div className="lg:col-span-2"><KeyScopeSwitch initial={data.key_scope ?? "all"} /></div>
          <div className="lg:col-span-2"><TokensPanel initial={tokens?.tokens ?? []} mcpUrl={tokens?.mcp_url ?? "/mcp"} /></div>
        </div>
      )}
    </AdminShell>
  );
}
