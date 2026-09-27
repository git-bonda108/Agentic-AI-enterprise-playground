"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ROLE_LABEL, type Role } from "@/lib/users";
import { formatDay } from "@/lib/format";

export type AdminUser = { id: string; name: string; email: string; role: Role; department: string; created_at: string };

export function UsersTable({ initial }: { initial: AdminUser[] }) {
  const [users, setUsers] = useState(initial);
  const save = async (u: AdminUser, patch: Partial<Pick<AdminUser, "role" | "department">>) => {
    const res = await fetch(`/api/pg/v1/admin/users/${u.id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(patch) });
    if (!res.ok) { toast.error("Could not save"); return; }
    const updated = await res.json();
    setUsers((list) => list.map((x) => (x.id === u.id ? { ...x, ...updated } : x)));
    toast.success(`${updated.name} is now ${ROLE_LABEL[updated.role as Role]} in ${updated.department}`);
  };
  return (
    <div className="overflow-x-auto rounded-2xl border bg-card">
      <table className="w-full text-xs" data-testid="users-table">
        <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
          <tr><th className="px-3 py-2">Person</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">Department</th><th className="px-3 py-2">First seen</th></tr>
        </thead>
        <tbody>
          {users.length === 0 && <tr><td colSpan={4} className="px-3 py-8 text-center text-muted-foreground">People appear here after their first sign-in.</td></tr>}
          {users.map((u) => (
            <tr key={u.id} className="border-t">
              <td className="px-3 py-2"><span className="block font-medium">{u.name}</span><span className="text-muted-foreground">{u.email}</span></td>
              <td className="px-3 py-2">
                <select aria-label={`Role for ${u.name}`} value={u.role} onChange={(e) => save(u, { role: e.target.value as Role })} className="h-8 rounded-lg border bg-background px-2 text-xs">
                  {(Object.keys(ROLE_LABEL) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                </select>
              </td>
              <td className="px-3 py-2">
                <input aria-label={`Department for ${u.name}`} defaultValue={u.department} onBlur={(e) => { if (e.target.value !== u.department) save(u, { department: e.target.value }); }} className="h-8 w-44 rounded-lg border bg-background px-2 text-xs" />
              </td>
              <td className="px-3 py-2 text-muted-foreground">{formatDay(u.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
