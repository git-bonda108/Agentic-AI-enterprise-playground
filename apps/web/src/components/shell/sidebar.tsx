"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { CURRENT_BATCH, NAV, TOTAL_BATCHES } from "@/lib/nav";

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();
  return (
    <aside
      aria-label="Primary navigation"
      className={cn(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200",
        collapsed ? "w-[68px]" : "w-[248px]",
      )}
    >
      <div className={cn("flex h-14 items-center gap-2.5 border-b border-sidebar-border px-3", collapsed && "justify-center px-0")}>
        <Link href="/home" className="flex items-center gap-2.5" aria-label="Enterprise AI Playground home">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg gradient-brand animate-gradient-shift text-sm font-semibold text-white shadow-md shadow-violet-900/30">✦</span>
          {!collapsed && (
            <span className="leading-tight">
              <span className="block text-[13px] font-semibold tracking-tight">AI Playground</span>
              <span className="block text-[10px] text-muted-foreground">Enterprise edition</span>
            </span>
          )}
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {NAV.map((section) => (
          <div key={section.title} className="mb-3">
            {!collapsed && (
              <p className="px-2 pb-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{section.title}</p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href;
                const pending = item.batch > CURRENT_BATCH;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      title={collapsed ? item.title : undefined}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "group relative flex h-8 items-center gap-2.5 rounded-lg px-2 text-[13px] transition-colors",
                        active ? "text-sidebar-accent-foreground" : "text-sidebar-foreground/90 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                        collapsed && "justify-center px-0",
                      )}
                    >
                      {active && (
                        <motion.span
                          layoutId="sidebar-active"
                          className="absolute inset-0 rounded-lg bg-sidebar-accent"
                          transition={{ type: "spring", stiffness: 500, damping: 40 }}
                        />
                      )}
                      <item.icon className={cn("relative size-4 shrink-0", active ? "text-brand-violet-soft" : "text-muted-foreground group-hover:text-foreground")} />
                      {!collapsed && <span className="relative truncate">{item.title}</span>}
                      {!collapsed && pending && (
                        <span className="relative ml-auto rounded-md border border-border px-1.5 py-px font-mono text-[9.5px] text-muted-foreground">B{item.batch}</span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className={cn("border-t border-sidebar-border p-2", collapsed && "flex justify-center")}>
        {!collapsed && (
          <div className="mb-2 rounded-lg border bg-card/60 p-2.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-medium">Build progress</span>
              <span className="font-mono text-muted-foreground">batch {CURRENT_BATCH} / {TOTAL_BATCHES}</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full gradient-brand" style={{ width: `${(CURRENT_BATCH / TOTAL_BATCHES) * 100}%` }} />
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex h-8 w-full items-center justify-center gap-2 rounded-lg text-xs text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
        >
          {collapsed ? <PanelLeftOpen className="size-4" /> : <><PanelLeftClose className="size-4" /> Collapse</>}
        </button>
      </div>
    </aside>
  );
}
