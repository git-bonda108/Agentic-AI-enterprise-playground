"use client";

import { useState } from "react";
import { Award, Medal } from "lucide-react";
import type { AchievementRecord, CommunityMe, LeaderboardRow } from "@/lib/playground-types";
import { cn } from "@/lib/utils";

const MEDAL = ["text-brand-amber", "text-slate-400", "text-amber-700"];

export function Leaderboard({ people, departments, me, points, days }: { people: LeaderboardRow[]; departments: LeaderboardRow[]; me: CommunityMe; points: Record<string, number>; days: number }) {
  const [by, setBy] = useState<"user" | "department">("user");
  const rows = by === "user" ? people : departments;
  return (
    <div className="mx-auto max-w-7xl">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">Community</p>
        <h1 className="text-2xl font-semibold tracking-tight">Leaderboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Adoption, reliability and savings over the last {days} days, by person and by team. Points are earned from the ledger and the evaluation engine, never typed in.</p>
      </div>

      <section className="mt-5 rounded-2xl border bg-card p-4" aria-label="Your achievements" data-testid="achievements">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="flex items-center gap-1.5 text-sm font-semibold"><Award className="size-4 text-brand-violet-soft" /> Your achievements · {me.unlocked} of {me.total}</p>
          <p className="text-xs text-muted-foreground">{me.rank ? `Rank ${me.rank} of ${me.people}` : "No activity yet"} · {me.points} points</p>
        </div>
        <ul className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {me.achievements.map((a: AchievementRecord) => (
            <li key={a.key} className={cn("rounded-xl border p-2.5", a.unlocked ? "border-brand-violet/50 bg-brand-violet/5" : "opacity-70")} title={a.description}>
              <p className="text-xs font-semibold">{a.name}</p>
              <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">{a.description}</p>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full", a.unlocked ? "bg-brand-violet" : "bg-brand-cyan")} style={{ width: `${Math.round((a.progress / a.target) * 100)}%` }} /></div>
              <p className="mt-1 font-mono text-[10px] text-muted-foreground">{a.unlocked ? `unlocked ${a.unlocked_at ? new Date(a.unlocked_at).toLocaleDateString() : ""}` : `${a.progress}/${a.target}`}</p>
            </li>
          ))}
        </ul>
      </section>

      <div className="mt-5 flex items-center gap-2">
        <div className="flex gap-1" role="tablist" aria-label="Board">
          {(["user", "department"] as const).map((b) => <button key={b} type="button" role="tab" aria-selected={by === b} onClick={() => setBy(b)} className={cn("h-8 rounded-lg border px-3 text-xs", by === b ? "border-brand-violet/60 bg-secondary" : "bg-card text-muted-foreground")}>{b === "user" ? "People" : "Departments"}</button>)}
        </div>
        <p className="text-[11px] text-muted-foreground">Points: {Object.entries(points).map(([k, v]) => `${k.replace("_", " ")} ×${v}`).join(" · ")}</p>
      </div>

      <div className="mt-3 overflow-hidden rounded-2xl border bg-card">
        <table className="w-full text-xs" data-testid="leaderboard-table">
          <thead className="bg-muted/60 text-left text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr><th className="px-3 py-2">#</th><th className="px-3 py-2">{by === "user" ? "Person" : "Department"}</th><th className="px-3 py-2 text-right">Points</th><th className="px-3 py-2 text-right">Requests</th><th className="px-3 py-2 text-right">Outcomes</th><th className="px-3 py-2 text-right">Savings</th><th className="px-3 py-2 text-right">Agents</th><th className="px-3 py-2 text-right">Suites</th><th className="px-3 py-2 text-right">Pass rate</th><th className="px-3 py-2 text-right">Badges</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${by}-${r.user_id ?? r.department}`} className="border-t">
                <td className="px-3 py-2">{r.rank <= 3 ? <Medal className={cn("size-4", MEDAL[r.rank - 1])} aria-label={`rank ${r.rank}`} /> : r.rank}</td>
                <td className="px-3 py-2 font-medium">{by === "user" ? <>{r.name} <span className="text-muted-foreground">· {r.department}</span></> : <>{r.department} <span className="text-muted-foreground">· {r.people} people</span></>}</td>
                <td className="px-3 py-2 text-right font-mono font-semibold">{r.points}</td>
                <td className="px-3 py-2 text-right font-mono">{r.requests}</td>
                <td className="px-3 py-2 text-right font-mono">{r.outcomes}</td>
                <td className="px-3 py-2 text-right font-mono">${r.savings_usd.toFixed(2)}</td>
                <td className="px-3 py-2 text-right font-mono">{r.agents}</td>
                <td className="px-3 py-2 text-right font-mono">{r.suites}</td>
                <td className="px-3 py-2 text-right font-mono">{r.pass_rate === null ? "–" : `${r.pass_rate}%`}</td>
                <td className="px-3 py-2 text-right font-mono">{r.achievements}{r.challenge_wins ? ` · ${r.challenge_wins} wins` : ""}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={10} className="px-3 py-6 text-center text-muted-foreground">No activity in this window yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
