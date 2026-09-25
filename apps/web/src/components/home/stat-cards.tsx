"use client";

import { motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { ArrowUpRight, Coins, Gauge, Layers, Users } from "lucide-react";
import { STATS, TOKEN_SERIES } from "@/lib/demo-data";
import { formatUsd, type UsageSummary } from "@/lib/playground-types";

const fmt = (n: number) => n.toLocaleString("en-US");

export function StatCards({ summary }: { summary: UsageSummary | null }) {
  const live = summary !== null;
  const credits = live ? Math.max(summary.credits_usd - summary.spend_month_usd, 0) : STATS.credits;
  const spendMonth = live ? summary.spend_month_usd : STATS.spendMonth;
  const spendLimit = live ? summary.monthly_cap_usd : STATS.spendLimit;
  const tokens7d = live ? summary.tokens_window : STATS.tokens7d;
  const cacheReuse = live ? summary.cache_reuse_ratio : STATS.cacheReuse;
  const activeUsers = live ? summary.active_users : STATS.activeUsers;
  const series = live && summary.by_day.some((d) => d.tokens > 0) ? summary.by_day.map((d) => ({ day: d.day.slice(5), tokens: d.tokens })) : TOKEN_SERIES;
  const spendPct = spendLimit > 0 ? Math.round((spendMonth / spendLimit) * 100) : 0;
  const tag = live ? (summary.scope === "organization" ? "live · org" : "live · you") : "seeded";
  const cards = [
    {
      key: "credits", icon: Coins, label: "Organization credits",
      value: `$${fmt(Math.round(credits))}`, foot: live ? "Remaining of the pooled allowance" : "Pooled fair-use allowance", accent: "text-brand-violet-soft",
    },
    {
      key: "spend", icon: Gauge, label: "Spend this month",
      value: formatUsd(spendMonth), foot: `${spendPct}% of $${fmt(spendLimit)} cap this month`, accent: "text-brand-pink", ring: spendPct,
    },
    {
      key: "tokens", icon: Layers, label: "Token volume, 7 days",
      value: tokens7d >= 1_000_000 ? `${(tokens7d / 1_000_000).toFixed(2)}M` : tokens7d >= 1000 ? `${(tokens7d / 1000).toFixed(1)}K` : String(tokens7d), foot: live ? `${summary.requests} requests · ${summary.errors} errors` : `+${Math.round(STATS.tokensDelta * 100)}% vs prior week`, accent: "text-brand-cyan", chart: true,
    },
    {
      key: "cache", icon: Users, label: "Prompt cache reuse",
      value: `${Math.round(cacheReuse * 100)}%`, foot: `${activeUsers} active ${activeUsers === 1 ? "person" : "people"} this week`, accent: "text-brand-emerald",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((c, i) => (
        <motion.div
          key={c.key}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 * i, duration: 0.35 }}
          className="card-hover relative overflow-hidden rounded-2xl border bg-card p-4"
        >
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <c.icon className={`size-3.5 ${c.accent}`} /> {c.label}
            </span>
            <span className={`rounded-full px-1.5 py-0.5 font-mono text-[9.5px] ${live ? "bg-brand-emerald/15 text-brand-emerald" : "bg-muted text-muted-foreground"}`}>{tag}</span>
          </div>
          <div className="mt-3 flex items-end justify-between gap-2">
            <p className="text-2xl font-semibold tracking-tight tabular-nums">{c.value}</p>
            {c.ring !== undefined && (
              <span
                className="grid size-10 place-items-center rounded-full text-[10px] font-medium"
                style={{ background: `conic-gradient(var(--brand-pink) ${c.ring * 3.6}deg, var(--muted) 0)` }}
                aria-label={`${c.ring} percent of cap used`}
              >
                <span className="grid size-7 place-items-center rounded-full bg-card">{c.ring}%</span>
              </span>
            )}
            {c.chart && (
              <div className="h-10 w-24" aria-hidden>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series} margin={{ top: 2, right: 0, bottom: 0, left: 0 }} accessibilityLayer={false}>
                    <defs>
                      <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--brand-cyan)" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="var(--brand-cyan)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="tokens" stroke="var(--brand-cyan)" strokeWidth={1.6} fill="url(#spark)" isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
          <p className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground">
            {c.key === "tokens" && <ArrowUpRight className="size-3 text-brand-emerald" />} {c.foot}
          </p>
        </motion.div>
      ))}
    </div>
  );
}
