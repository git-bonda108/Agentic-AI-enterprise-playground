"use client";

import { Check, Lock, ShieldCheck } from "lucide-react";
import type { Hardening } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

/** Five rungs from Draft to Production, each lit only by evidence. */
export function HardeningLadder({ ladder, compact = false }: { ladder: Hardening; compact?: boolean }) {
  const ev = ladder.evidence;
  const evidenceFor: Record<number, string> = {
    0: "Always available.",
    1: `${ev.cases} cases in the largest suite, ${ev.evaluations} evaluation${ev.evaluations === 1 ? "" : "s"} completed.`,
    2: ev.latest_pass_rate === null ? "No evaluation yet." : `Latest run ${ev.latest_pass_rate}% pass rate, gate ${ev.latest_gate_passed ? "cleared" : "not cleared"}.`,
    3: ev.canary_enabled ? `Canary on, ${ev.consecutive_passes} consecutive stable run${ev.consecutive_passes === 1 ? "" : "s"}.` : "No canary scheduled.",
    4: ladder.last_promotion ? `${ladder.last_promotion.by === "canary" ? "Demoted by a canary" : "Promoted by an admin"}: ${ladder.last_promotion.note || "no note"}.` : "Needs an administrator's promotion.",
  };
  return (
    <ol className={cn("grid gap-2", compact ? "grid-cols-5" : "sm:grid-cols-5")} aria-label="Hardening ladder" data-testid="hardening-ladder">
      {ladder.levels.map((l) => {
        const reached = l.level <= ladder.level;
        const current = l.level === ladder.level;
        return (
          <li key={l.level} className={cn("rounded-xl border p-2.5", reached ? "border-brand-violet/50 bg-brand-violet/5" : "opacity-70", current && "glow-violet")}>
            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <span className={cn("grid size-5 place-items-center rounded-full text-[10px]", reached ? "bg-brand-violet text-white" : "bg-muted text-muted-foreground")}>{reached ? <Check className="size-3" /> : l.level === 4 ? <Lock className="size-3" /> : l.level}</span>
              {l.name}{current && <ShieldCheck className="ml-auto size-3.5 text-brand-violet-soft" aria-label="current level" />}
            </div>
            {!compact && <p className="mt-1 text-[11px] text-muted-foreground">{l.requirement}</p>}
            {!compact && <p className="mt-1 text-[11px]">{evidenceFor[l.level]}</p>}
          </li>
        );
      })}
    </ol>
  );
}
