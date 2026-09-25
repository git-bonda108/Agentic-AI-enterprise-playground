"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { NAV } from "@/lib/nav";

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Go anywhere" description="Jump to a page, model or blueprint">
      <Command>
      <CommandInput placeholder="Search pages, models, blueprints…" />
      <CommandList>
        <CommandEmpty>Nothing matches yet.</CommandEmpty>
        {NAV.map((section) => (
          <CommandGroup key={section.title} heading={section.title}>
            {section.items.map((item) => (
              <CommandItem
                key={item.href}
                value={`${section.title} ${item.title}`}
                onSelect={() => {
                  onOpenChange(false);
                  router.push(item.href);
                }}
              >
                <item.icon className="size-4 text-muted-foreground" />
                <span>{item.title}</span>
                <span className="ml-auto text-xs text-muted-foreground">{item.batch === 0 ? "live" : `batch ${item.batch}`}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        ))}
      </CommandList>
      </Command>
    </CommandDialog>
  );
}
