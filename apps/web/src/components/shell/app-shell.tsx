"use client";

import { useState } from "react";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar, type ShellUser } from "@/components/shell/topbar";
import { CommandPalette } from "@/components/shell/command-palette";
import { useStoredBoolean } from "@/lib/use-client-store";

export function AppShell({ user, children }: { user: ShellUser; children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useStoredBoolean("playground.sidebar.collapsed", false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar user={user} onOpenSearch={() => setPaletteOpen(true)} />
        <main id="main" className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
