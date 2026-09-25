"use client";

import { ChevronDown, Sparkles } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { CatalogModel } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

export const TIER_DOT: Record<string, string> = {
  Frontier: "bg-brand-violet-soft",
  Premium: "bg-brand-pink",
  Workhorse: "bg-brand-cyan",
  Economy: "bg-brand-emerald",
};

export function ModelPicker({ models, value, onChange, compact = false, smartEnabled = false }: { models: CatalogModel[]; value: string; onChange: (id: string) => void; compact?: boolean; smartEnabled?: boolean }) {
  const isSmart = value === "smart";
  const current = models.find((m) => m.id === value) ?? models[0];
  const providers = Array.from(new Set(models.map((m) => m.provider)));
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Choose model"
        className={cn("flex h-8 items-center gap-2 rounded-lg border bg-card px-2.5 text-xs hover:border-brand-violet/40", compact && "h-7 text-[11px]")}
      >
        {isSmart ? <Sparkles className="size-3.5 text-brand-violet-soft" /> : <span className={cn("size-1.5 rounded-full", TIER_DOT[current?.tier ?? "Economy"])} />}
        <span className="font-medium">{isSmart ? "Smart routing" : current?.name ?? value}</span>
        <span className="text-muted-foreground">{isSmart ? "auto" : current?.provider}</span>
        <ChevronDown className="size-3.5 text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-[420px] w-80">
        {smartEnabled && (
          <DropdownMenuGroup>
            <DropdownMenuItem onClick={() => onChange("smart")} className="flex items-center gap-2">
              <Sparkles className="size-3.5 text-brand-violet-soft" />
              <span className="flex-1">Smart routing</span>
              <span className="font-mono text-[10px] text-muted-foreground">cheapest fit</span>
            </DropdownMenuItem>
          </DropdownMenuGroup>
        )}
        {providers.map((p) => (
          <DropdownMenuGroup key={p}>
            <DropdownMenuLabel className="text-[10.5px] uppercase tracking-wider text-muted-foreground">{p}</DropdownMenuLabel>
            {models.filter((m) => m.provider === p).map((m) => (
              <DropdownMenuItem key={m.id} onClick={() => onChange(m.id)} disabled={!m.available} className="flex items-center gap-2">
                <span className={cn("size-1.5 rounded-full", TIER_DOT[m.tier])} />
                <span className="flex-1 truncate">{m.name}</span>
                <span className="font-mono text-[10px] text-muted-foreground">${m.input_per_m}/${m.output_per_m}</span>
                {!m.available && <span className="rounded bg-muted px-1 text-[9px] text-muted-foreground">no key</span>}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
