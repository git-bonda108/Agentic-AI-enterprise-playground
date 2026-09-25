import type { Metadata } from "next";
import { apiGet } from "@/lib/api-server";
import { AdminShell } from "@/components/admin/admin-shell";
import { UsersTable, type AdminUser } from "@/components/admin/users-table";

export const metadata: Metadata = { title: "Users" };
export const dynamic = "force-dynamic";

export default async function AdminUsersPage() {
  const data = await apiGet<{ users: AdminUser[] }>("/v1/admin/users");
  return (
    <AdminShell title="Users" blurb="People, roles and departments. Roles decide which models and budgets apply." active="/admin/users">
      <UsersTable initial={data?.users ?? []} />
    </AdminShell>
  );
}
