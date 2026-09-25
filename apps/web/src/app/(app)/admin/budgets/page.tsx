import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { AdminShell } from "@/components/admin/admin-shell";
import { BudgetsEditor, type BudgetsData } from "@/components/admin/budgets-editor";
import type { AlertItem } from "@/lib/playground-types";

export const metadata: Metadata = { title: "Budgets" };
export const dynamic = "force-dynamic";

export default async function AdminBudgetsPage() {
  const [budgets, users, alerts] = await Promise.all([
    apiGet<BudgetsData>("/v1/admin/budgets"),
    apiGet<{ users: { id: string; name: string }[] }>("/v1/admin/users"),
    apiGet<{ alerts: AlertItem[] }>("/v1/alerts"),
  ]);
  return (
    <AdminShell title="Budgets" blurb="Monthly caps for the organization, departments and people, with alerts at 50, 80 and 100 percent." active="/admin/budgets">
      {budgets ? <BudgetsEditor initial={budgets} people={users?.users ?? []} alerts={alerts?.alerts ?? []} /> : <p className="text-sm text-muted-foreground">API unreachable.</p>}
    </AdminShell>
  );
}
