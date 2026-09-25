export type CatalogModel = {
  id: string;
  name: string;
  provider: string;
  tier: "Frontier" | "Premium" | "Workhorse" | "Economy";
  litellm_model: string;
  input_per_m: number;
  output_per_m: number;
  cached_input_per_m: number | null;
  context: number;
  tags: string[];
  env_key: string;
  notes: string;
  lifecycle: string;
  docs_url: string;
  capabilities: string[];
  available: boolean;
};

export type ChatParams = { temperature: number; max_tokens: number; top_p: number; system: string };

export type Usage = {
  tokens_in: number;
  tokens_out: number;
  tokens_cached: number;
  cost_usd: number;
  latency_ms: number;
  model: string;
  provider: string;
  message_id: string | null;
  conversation_id: string | null;
  routed?: boolean;
  routed_tier?: string | null;
  savings_usd?: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string;
  usage?: Usage | null;
  error?: string | null;
  streaming?: boolean;
};

export type ConversationSummary = {
  id: string;
  title: string;
  model: string;
  tags: string[];
  pinned: boolean;
  system_prompt: string;
  created_at: string;
  updated_at: string;
  has_messages: boolean;
};

export type ConversationDetail = ConversationSummary & {
  messages: { id: string; role: "user" | "assistant"; content: string; model: string | null; tokens_in: number; tokens_out: number; cost_usd: number; latency_ms: number }[];
};

export type UsageSummary = {
  scope: "organization" | "me";
  days: number;
  credits_usd: number;
  monthly_cap_usd: number;
  spend_month_usd: number;
  spend_window_usd: number;
  tokens_window: number;
  cache_reuse_ratio: number;
  requests: number;
  errors: number;
  active_users: number;
  by_day: { day: string; tokens: number; cost_usd: number; requests: number }[];
  by_model: { model: string; provider: string; tokens: number; cost_usd: number; requests: number }[];
  by_feature: { feature: string; tokens: number; cost_usd: number; requests: number }[];
  by_user: { user_id: string; name?: string; department?: string; tokens: number; cost_usd: number; requests: number }[];
};

export const DEFAULT_PARAMS: ChatParams = { temperature: 0.7, max_tokens: 2048, top_p: 1, system: "" };

export function formatUsd(v: number): string {
  if (v === 0) return "$0.00";
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(2)}`;
}

export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export type RouteDecision = {
  tier: string;
  model: string;
  reason: string;
  baseline_model: string;
  est_cost_usd: number;
  est_baseline_cost_usd: number;
  est_savings_pct: number;
};

export type BreakdownRow = {
  key: string; label: string; tokens_in: number; tokens_out: number; tokens_cached: number; cost_usd: number;
  requests: number; errors: number; savings_usd: number; avg_latency_ms: number;
};

export type Breakdown = {
  scope: "organization" | "me";
  by: string;
  days: number;
  totals: { cost_usd: number; spend_month_usd: number; forecast_month_usd: number; savings_usd: number; routed_requests: number; requests: number; errors: number; tokens: number };
  rows: BreakdownRow[];
};

export type AlertItem = {
  id: string; scope: string; key: string; label: string; threshold: number; period: string; spend_usd: number; cap_usd: number; acknowledged: boolean; created_at: string;
};

export const PROVIDER_ART: Record<string, string> = {
  Anthropic: "linear-gradient(135deg,#5b8def,#7c3aed)",
  OpenAI: "linear-gradient(135deg,#0ea5e9,#06b6d4)",
  Google: "linear-gradient(135deg,#f59e0b,#ec4899)",
  DeepSeek: "linear-gradient(135deg,#34d399,#0d9488)",
  "Azure OpenAI": "linear-gradient(135deg,#2563eb,#0891b2)",
  "Hugging Face": "linear-gradient(135deg,#fbbf24,#f97316)",
};

export type BlueprintManifest = {
  id: string; name: string; family: string; pattern: string; summary: string; description: string;
  tiers: Record<string, string>;
  graph: { nodes: { id: string; label: string; kind: "tool" | "llm" | "gate" | "human" }[]; edges: [string, string, string?][]; columns: string[][] };
  samples: { name: string; input: Record<string, unknown> }[];
  datasets: string[]; flavors: string[]; review_gates: string[]; dashboard: string[]; links: Record<string, string>;
  input_schema: Record<string, string>; batch: number;
};

export type RunStep = { node: string; kind: string; summary: string; detail: Record<string, unknown>; at: string; ms: number };

export type RunReview = { question: string; options?: string[]; items?: { label: string; detail: string }[]; free_text?: string; context?: string };

export type RunRecord = {
  id: string; blueprint_id: string; blueprint_name: string; user_id: string; user_name: string | null;
  status: "queued" | "running" | "waiting_review" | "completed" | "failed";
  input: Record<string, unknown>; output: Record<string, unknown> | null; steps: RunStep[]; review: RunReview | null; error: string | null;
  cost_usd: number; tokens_in: number; tokens_out: number; created_at: string; updated_at: string; finished_at: string | null;
};

export type DatasetInfo = { id: string; file: string; title: string; source: string; used_by: string[]; rows: number; preview: Record<string, unknown>[] };

export type CatalogEntry = {
  id: string; name: string; family: string; group: string;
  source: { repo: string; path: string; license: string; url: string; title: string };
  summary: string; instructions_preview: string; instructions?: string; instructions_truncated: boolean;
  tools: string[]; model_hint: string; tags: string[]; runnable: boolean; tier: string;
  knowledge?: string[]; starter_prompts?: string[]; flavors?: string[]; samples?: { name: string; input: Record<string, unknown> }[]; links?: Record<string, string>; input_schema?: Record<string, string>;
  curation: { status: "green" | "red" | "unreviewed"; reasons: string[]; reviewed_at?: string };
};

export type CatalogStats = { total: number; by_family: Record<string, number>; green: number; red: number; runnable: number; sources: string[] };

export type FrameworkInfo = { id: string; name: string; install: string; docs: string; license: string; hosted: string; language: string };
export type CloudInfo = { id: string; name: string; runtime: string; pricing: string; pricing_url: string; docs: string; prereq: string };
export type CustomAgent = { id: string; name: string; description: string; instructions: string; knowledge: string[]; tools: string[]; skills: string[]; starters: string[]; published: boolean; owner_id: string; created_at: string };

export type Connector = {
  id: string; title: string; description: string; version: string; publisher: string; category: string;
  transport: string; remote_url: string; package: { registry: string; identifier: string; version: string; transport: string } | null;
  env_vars: string[]; repo_url: string; website: string; status: string; approval: "pending" | "approved" | "blocked";
  approved_by: string | null; approval_note: string; signals: number; registry_updated_at: string; install: Record<string, unknown>;
};
export type ConnectorStats = { total: number; by_approval: Record<string, number>; by_transport: Record<string, number>; by_category: Record<string, number>; categories: string[]; registry_newest: string | null };
export type ProbeResult = { ok: boolean; server: { name?: string; version?: string }; protocol: string; tools: { name: string; description: string; input_schema: Record<string, unknown> }[]; tool_count: number; latency_ms: number; auth_required: boolean; error: string | null };

export type Skill = { id: string; name: string; description: string; source: { repo: string; path: string; license: string; url: string; title: string }; category: string; tags: string[]; words: number; preview: string; body?: string; body_truncated: boolean };
export type SkillStats = { total: number; by_category: Record<string, number>; by_source: Record<string, number> };

export type KnowledgeSpace = { id: string; name: string; description: string; visibility: "private" | "department" | "org"; department: string; embedding_model: string; embedding_name: string; doc_count: number; chunk_count: number; owner_id: string; owner_name: string | null; created_at: string; updated_at: string };
export type KnowledgeDocument = { id: string; space_id: string; title: string; source_type: string; source_ref: string; bytes: number; chunk_count: number; tokens: number; cost_usd: number; has_graph: boolean; created_at: string };
export type SearchHit = { chunk_id: string; doc_id: string; title: string; source_type: string; ordinal: number; text: string; meta: Record<string, unknown>; score: number; dense: number; sparse: number; cite: string };
export type GraphNode = { id: string; label: string; kind: string; file: string; line: number; degree: number; community: number; doc_id?: string };
export type GraphEdge = { source: string; target: string; kind: string };
export type EmbeddingModel = { id: string; name: string; provider: string; dims: number; price_per_m: number; note: string; available: boolean };
export type ApiTokenInfo = { id: string; name: string; prefix: string; created_at: string; last_used_at: string | null };
