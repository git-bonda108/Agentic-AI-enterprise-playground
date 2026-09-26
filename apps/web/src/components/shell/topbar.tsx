"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, ChevronRight, LogOut, Search } from "lucide-react";
import type { AlertItem } from "@/lib/playground-types";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { KeysDrawer } from "@/components/shell/keys-drawer";
import { signOutAction } from "@/app/login/actions";
import { findNavItem } from "@/lib/nav";
import { ROLE_LABEL, type Role } from "@/lib/users";
import { cn } from "@/lib/utils";

export type ShellUser = { name: string; email: string; role: Role; department: string; image?: string | null };

export function Topbar({ user, onOpenSearch }: { user: ShellUser; onOpenSearch: () => void }) {
  const pathname = usePathname();
  const match = findNavItem(pathname);
  const [api, setApi] = useState<"checking" | "online" | "offline">("checking");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then((r) => r.json())
      .then((j) => { if (!cancelled) setApi(j.api === "online" ? "online" : "offline"); })
      .catch(() => { if (!cancelled) setApi("offline"); });
    const loadAlerts = () =>
      fetch("/api/pg/v1/alerts").then((r) => (r.ok ? r.json() : { alerts: [] })).then((j) => { if (!cancelled) setAlerts(j.alerts ?? []); }).catch(() => {});
    void loadAlerts();
    // The playground raises this after a budget warning or a blocked call so the badge updates at once.
    window.addEventListener("playground:alerts", loadAlerts);
    const timer = setInterval(loadAlerts, 30_000);
    return () => { cancelled = true; window.removeEventListener("playground:alerts", loadAlerts); clearInterval(timer); };
  }, [pathname]);
  const unread = alerts.filter((a) => !a.acknowledged).length;

  const initials = user.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md">
      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1 text-sm">
        <Link href="/home" className="text-muted-foreground hover:text-foreground">Playground</Link>
        {match && (
          <>
            <ChevronRight className="size-3.5 text-muted-foreground/60" />
            <span className="text-muted-foreground">{match.section.title}</span>
            <ChevronRight className="size-3.5 text-muted-foreground/60" />
            <span className="truncate font-medium">{match.item.title}</span>
          </>
        )}
      </nav>

      <div className="ml-auto flex items-center gap-1.5">
        <button
          type="button"
          onClick={onOpenSearch}
          className="hidden h-8 items-center gap-2 rounded-lg border bg-card px-2.5 text-xs text-muted-foreground hover:border-brand-violet/40 hover:text-foreground sm:flex"
          aria-label="Search the playground"
        >
          <Search className="size-3.5" />
          <span>Search…</span>
          <kbd className="ml-4 rounded border bg-muted px-1.5 font-mono text-[10px]">⌘K</kbd>
        </button>

        <span
          className="hidden items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] text-muted-foreground md:flex"
          title="Backend API status"
        >
          <span className={cn("size-1.5 rounded-full", api === "online" ? "bg-brand-emerald animate-pulse-glow" : api === "offline" ? "bg-brand-rose" : "bg-muted-foreground")} />
          API {api}
        </span>
        <KeysDrawer />

        <DropdownMenu>
          <DropdownMenuTrigger aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"} className="relative grid size-8 place-items-center rounded-lg hover:bg-muted">
            <Bell className="size-4" />
            {unread > 0 && <span className="absolute -right-0.5 -top-0.5 grid size-4 place-items-center rounded-full bg-brand-rose text-[9px] font-semibold text-white">{unread}</span>}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Alerts</DropdownMenuLabel>
              {alerts.length === 0 && <DropdownMenuItem disabled>No alerts this month</DropdownMenuItem>}
              {alerts.slice(0, 6).map((a) => (
                <DropdownMenuItem key={a.id} className={a.acknowledged ? "opacity-60" : ""} title={a.message || undefined}>
                  <span className={`size-1.5 shrink-0 rounded-full ${a.kind === "canary" ? "bg-brand-pink" : a.threshold >= 100 ? "bg-brand-rose" : "bg-brand-amber"}`} />
                  <span className="truncate">{a.kind === "canary" ? a.label : `${a.label} at ${a.threshold}%`}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem render={<Link href="/admin/budgets" />}>Manage budgets</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ThemeToggle />

        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="Account menu"
            className="ml-1 flex h-8 items-center gap-2 rounded-full border bg-card pl-0.5 pr-2 text-xs hover:border-brand-violet/40"
          >
            <span className="grid size-7 place-items-center rounded-full gradient-brand text-[10px] font-semibold text-white">{initials}</span>
            <span className="hidden max-w-[120px] truncate sm:block">{user.name}</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-60">
            <DropdownMenuGroup>
              <DropdownMenuLabel>
                <span className="block text-sm font-medium">{user.name}</span>
                <span className="block text-xs text-muted-foreground">{user.email}</span>
                <span className="mt-1 inline-block rounded-md bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-secondary-foreground">
                  {ROLE_LABEL[user.role]} · {user.department}
                </span>
              </DropdownMenuLabel>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => { void signOutAction(); }}
            >
              <LogOut className="size-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
