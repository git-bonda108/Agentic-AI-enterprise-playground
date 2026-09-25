import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { AdminShell } from "@/components/admin/admin-shell";
import { PoliciesEditor, type PolicyRow } from "@/components/admin/policies-editor";

export const metadata: Metadata = { title: "Policies" };
export const dynamic = "force-dynamic";

export default async function AdminPoliciesPage() {
  const data = await apiGet<{ policies: PolicyRow[]; tiers: string[]; providers: string[] }>("/v1/admin/policies");
  return (
    <AdminShell title="Policies" blurb="Which model tiers and providers each role may use, the output ceiling, and whether Smart routing is on." active="/admin/policies">
      {data ? <PoliciesEditor initial={data.policies} tiers={data.tiers} providers={data.providers} /> : <p className="text-sm text-muted-foreground">API unreachable.</p>}
    </AdminShell>
  );
}
