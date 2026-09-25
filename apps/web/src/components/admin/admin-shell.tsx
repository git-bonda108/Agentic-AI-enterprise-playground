import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { auth } from "@/auth";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/admin/users", label: "Users" }, { href: "/admin/policies", label: "Policies" }, { href: "/admin/budgets", label: "Budgets" }, { href: "/admin/settings", label: "Settings" },
];

export async function AdminShell({ title, blurb, active, children }: { title: string; blurb: string; active: string; children: React.ReactNode }) {
  const session = await auth();
  const isAdmin = session?.user?.role === "admin";
  return (
    <div className="mx-auto max-w-6xl">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Admin</p>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{blurb}</p>
      <nav className="mt-4 flex gap-1 border-b" aria-label="Admin sections">
        {TABS.map((t) => (
          <Link key={t.href} href={t.href} aria-current={active === t.href ? "page" : undefined} className={cn("-mb-px border-b-2 px-3 py-2 text-sm", active === t.href ? "border-brand-violet text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}>{t.label}</Link>
        ))}
      </nav>
      <div className="mt-5">
        {isAdmin ? children : (
          <div className="rounded-2xl border bg-card p-8 text-center">
            <ShieldAlert className="mx-auto size-8 text-brand-amber" />
            <p className="mt-3 text-sm font-medium">Admin role required</p>
            <p className="mt-1 text-xs text-muted-foreground">You are signed in as {session?.user?.role}. Ask an administrator for access, or sign in as Satya Bonda in this demo environment.</p>
          </div>
        )}
      </div>
    </div>
  );
}
