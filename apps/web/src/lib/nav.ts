import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard, Compass, Hammer, FlaskConical, Activity, Users, ShieldCheck,
  Boxes, Blocks, Layers, Cloud, Plug, Sparkles, MessagesSquare, Bot, NotebookPen,
  BookOpen, Database, ClipboardCheck, Radar, Play, Waypoints, Coins, TrendingUp,
  Trophy, Medal, Star, UserCog, ScrollText, Wallet, Settings,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  /** Batch in which the page becomes functional. 0 means live now. */
  batch: number;
  blurb: string;
};

export type NavSection = {
  title: string;
  icon: LucideIcon;
  href: string;
  items: NavItem[];
};

export const NAV: NavSection[] = [
  {
    title: "Home", icon: LayoutDashboard, href: "/home",
    items: [{ title: "Console", href: "/home", icon: LayoutDashboard, batch: 0, blurb: "Credits, spend, tokens, models and where to start." }],
  },
  {
    title: "Discover", icon: Compass, href: "/discover/models",
    items: [
      { title: "Models", href: "/discover/models", icon: Boxes, batch: 2, blurb: "Every model, every provider, one price sheet." },
      { title: "Blueprints", href: "/discover/blueprints", icon: Blocks, batch: 4, blurb: "Runnable agent packages across six families." },
      { title: "Frameworks", href: "/discover/frameworks", icon: Layers, batch: 5, blurb: "The same agent as OpenAI Agents SDK, LangGraph, CrewAI, Agent Framework, ADK." },
      { title: "Clouds", href: "/discover/clouds", icon: Cloud, batch: 5, blurb: "Deploy to Foundry, AgentCore or Google Agent Runtime with real commands." },
      { title: "Connectors", href: "/discover/connectors", icon: Plug, batch: 6, blurb: "MCP servers from the official registry, approved by your admins." },
      { title: "Skills", href: "/discover/skills", icon: Sparkles, batch: 6, blurb: "SKILL.md packs you can attach to any agent." },
    ],
  },
  {
    title: "Build", icon: Hammer, href: "/build/playground",
    items: [
      { title: "Playground", href: "/build/playground", icon: MessagesSquare, batch: 1, blurb: "Chat, compare four models, see the code." },
      { title: "Agent Hub", href: "/build/agents", icon: Bot, batch: 3, blurb: "Your configured blueprints and their runs." },
      { title: "Notebooks", href: "/build/notebooks", icon: NotebookPen, batch: 5, blurb: "In-browser or sandboxed Python, pre-filled from a run." },
      { title: "Knowledge", href: "/build/knowledge", icon: BookOpen, batch: 6, blurb: "Knowledge Spaces over your documents and repos." },
      { title: "Data", href: "/build/data", icon: Database, batch: 3, blurb: "Mock datasets to test any blueprint safely." },
    ],
  },
  {
    title: "Evaluate", icon: FlaskConical, href: "/evaluate/evals",
    items: [
      { title: "Evals", href: "/evaluate/evals", icon: ClipboardCheck, batch: 7, blurb: "Golden sets, rubrics and gates, explained as you build them." },
      { title: "Canary", href: "/evaluate/canary", icon: Radar, batch: 7, blurb: "Nightly reruns, drift alerts, automatic rollback." },
    ],
  },
  {
    title: "Operate", icon: Activity, href: "/operate/runs",
    items: [
      { title: "Runs", href: "/operate/runs", icon: Play, batch: 3, blurb: "Every agent run with its state and review inbox." },
      { title: "Traces", href: "/operate/traces", icon: Waypoints, batch: 3, blurb: "Step-by-step traces with tokens and latency." },
      { title: "Cost", href: "/operate/cost", icon: Coins, batch: 2, blurb: "Seven layers of cost, from org to conversation." },
      { title: "Adoption", href: "/operate/adoption", icon: TrendingUp, batch: 8, blurb: "Hours per feature, cost per outcome, ROI matrix." },
    ],
  },
  {
    title: "Community", icon: Users, href: "/community/showcase",
    items: [
      { title: "Showcase", href: "/community/showcase", icon: Star, batch: 8, blurb: "Published agents and use cases from your colleagues." },
      { title: "Challenges", href: "/community/challenges", icon: Trophy, batch: 8, blurb: "Time-boxed builds judged by rubric." },
      { title: "Leaderboard", href: "/community/leaderboard", icon: Medal, batch: 8, blurb: "Adoption, reliability and savings, by person and team." },
    ],
  },
  {
    title: "Admin", icon: ShieldCheck, href: "/admin/users",
    items: [
      { title: "Users", href: "/admin/users", icon: UserCog, batch: 2, blurb: "People, roles and groups from your identity provider." },
      { title: "Policies", href: "/admin/policies", icon: ScrollText, batch: 2, blurb: "Who may use which model, tool and data class." },
      { title: "Budgets", href: "/admin/budgets", icon: Wallet, batch: 2, blurb: "Caps per user and pooled limits with alerts." },
      { title: "Settings", href: "/admin/settings", icon: Settings, batch: 2, blurb: "Providers, keys, theme and integrations." },
    ],
  },
];

export const ALL_ITEMS: NavItem[] = NAV.flatMap((s) => s.items);

export function findNavItem(pathname: string): { section: NavSection; item: NavItem } | null {
  for (const section of NAV) {
    for (const item of section.items) {
      if (item.href === pathname) return { section, item };
    }
  }
  return null;
}

export const CURRENT_BATCH = 5;
