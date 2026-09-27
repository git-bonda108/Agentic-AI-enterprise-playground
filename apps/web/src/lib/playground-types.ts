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
  /** Which key would serve this model for the caller: personal | platform | fake | none. */
  key_source?: "personal" | "platform" | "fake" | "none";
};

export type ProviderKeyStatus = {
  provider: string;
  env_key: string;
  key_page: string;
  docs: string;
  pricing: string;
  prefix: string;
  needs_base: boolean;
  models: number;
  platform_configured: boolean;
  personal: { last4: string; extra: Record<string, string>; created_at: string; last_used_at: string | null } | null;
  source: "personal" | "platform" | "fake" | "none";
  usable: boolean;
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
  hours: UsageHours;
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
  filters: Record<string, string>;
  totals: { cost_usd: number; tokens_in: number; tokens_out: number; tokens_cached: number; spend_month_usd: number; forecast_month_usd: number; savings_usd: number; routed_requests: number; requests: number; errors: number; tokens: number };
  rows: BreakdownRow[];
};

export type AlertItem = {
  id: string; scope: string; key: string; label: string; threshold: number; period: string; spend_usd: number; cap_usd: number; kind?: "budget" | "canary"; message?: string; acknowledged: boolean; created_at: string;
};

export type EvalCase = { id: string; name?: string; input: Record<string, unknown>; resume?: unknown; expect: Record<string, unknown>; from_run_id?: string };
export type EvalRubric = { criteria: { id: string; weight: number }[]; pass_threshold: number };
export type EvalGate = { min_pass_rate: number; max_cost_per_case_usd: number; max_p95_ms: number };
export type EvalSummary = { cases: number; passed: number; pass_rate: number; avg_score: number | null; cost_usd: number; cost_per_case_usd: number; p95_ms: number; gate: Record<string, boolean>; gate_passed: boolean };
export type EvalDrift = { pass_rate_drop: number; cost_delta_pct: number; latency_delta_pct: number; verdict: "stable" | "drift"; reasons: string[]; actions?: string[] };
export type EvalCheck = { check: string; passed: boolean; detail: string };
export type EvalScore = { criterion: string; score: number | null; rationale: string; model: string; cost_usd?: number };
export type EvalCaseResult = { case_id: string; name?: string; run_id: string | null; status: string; passed: boolean; checks: EvalCheck[]; scores: EvalScore[]; avg_score: number | null; cost_usd: number; ms: number; error: string | null };
export type EvalRunRecord = { id: string; suite_id: string; blueprint_id: string; user_id: string; kind: "manual" | "canary"; status: "queued" | "running" | "completed" | "failed"; summary: Partial<EvalSummary>; baseline_run_id: string | null; drift: EvalDrift | null; agent_version: number | null; error: string | null; created_at: string; finished_at: string | null; results?: EvalCaseResult[] };
export type CanaryInfo = { id: string; suite_id: string; enabled: boolean; hour_utc: number; auto_rollback: boolean; max_pass_rate_drop: number; max_cost_increase_pct: number; max_latency_increase_pct: number; last_run_id: string | null; next_due_at: string | null; consecutive_passes: number };
export type EvalSuiteRecord = { id: string; owner_id: string | null; blueprint_id: string; blueprint_name: string; name: string; description: string; cases: EvalCase[]; rubric: EvalRubric; gate: EvalGate; system: boolean; case_count: number; last_run: EvalRunRecord | null; canary: CanaryInfo | null; created_at: string; updated_at: string; can_edit?: boolean; hardening?: Hardening };
export type HardeningLevel = { level: number; name: string; requirement: string };
export type Hardening = { blueprint_id: string; level: number; achieved: number; name: string; levels: HardeningLevel[]; evidence: { suites: number; cases: number; evaluations: number; latest_pass_rate: number | null; latest_gate_passed: boolean; canary_enabled: boolean; consecutive_passes: number; last_canaries_stable: boolean }; last_promotion: { level: number; by: string; note: string; at: string } | null };
export type RubricCriterion = { id: string; name: string; description: string; why: string };
export type CheckType = { id: string; label: string; example: string; explain: string };
export type EvalLibrary = { rubric: RubricCriterion[]; checks: CheckType[]; levels: HardeningLevel[]; default_gate: EvalGate; default_rubric: EvalRubric };
export type CanaryBoardRow = CanaryInfo & { suite: EvalSuiteRecord | null; last_run: EvalRunRecord | null; hardening: Hardening | null };

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

export type DatasetColumn = { name: string; type: string; example: string | number | boolean };
export type DatasetInfo = {
  id: string; file: string; title: string; source: string; used_by: string[]; rows: number; preview: Record<string, unknown>[];
  columns: DatasetColumn[]; shape: "table" | "keyed"; licence: { name: string; url: string }; modeled_on: { name: string; url: string; licence: string; licence_url: string } | null;
  notebook: string | null; snippet: string; download: { csv: string; json: string };
};
export type DataSource = { id: string; name: string; url: string; kind: string; licence: string; install: string; python: string; docs: string; good_for: string };
export type LedgerEvent = {
  id: string; created_at: string; user: string; department: string; feature: string; model: string; provider: string; tokens_in: number; tokens_out: number; tokens_cached: number;
  cost_usd: number; latency_ms: number; status: string; key_source: string; routed: boolean; savings_usd: number; conversation: string; conversation_id: string | null;
  run_id: string | null; blueprint: string; blueprint_id: string | null; trace_id: string | null;
};
export type LedgerPage = { scope: "organization" | "me"; days: number; filters: Record<string, string>; total: number; offset: number; limit: number; rows: LedgerEvent[] };
export type UsageHours = { window: Record<string, number>; previous: Record<string, number>; people: Record<string, number>; days: number };

export type CatalogEntry = {
  id: string; name: string; family: string; group: string;
  source: { repo: string; path: string; license: string; url: string; title: string };
  summary: string; instructions_preview: string; instructions?: string; instructions_truncated: boolean;
  tools: string[]; model_hint: string; tags: string[]; runnable: boolean; tier: string;
  knowledge?: string[]; starter_prompts?: string[]; flavors?: string[]; samples?: { name: string; input: Record<string, unknown> }[]; links?: Record<string, string>; input_schema?: Record<string, string>;
  curation: { status: "green" | "red" | "unreviewed"; reasons: string[]; reviewed_at?: string };
  /** Gen AI: one model call with instructions and knowledge. Agentic AI: several steps, tools, review or coordination. */
  category: "Gen AI" | "Agentic AI";
};

export type CatalogStats = { total: number; by_family: Record<string, number>; by_category: Record<string, number>; green: number; red: number; runnable: number; sources: string[] };

export type LowcodeStudio = { id: "langflow" | "n8n" | "copilot"; name: string; artefact: string; install: string; steps: string[]; docs: string; mcp_docs: string; install_docs: string; artefact_url?: string; download_url?: string };
export type LowcodePlatform = { id: string; name: string; vendor: string; kind: string; licence: string; hosting: string; mcp: string; best_for: string; playground: string; url: string; docs: string; pricing: string };
export type LowcodeTracks = { blueprint_id: string; name: string; category: "Gen AI" | "Agentic AI"; category_blurb: string; lowcode: LowcodeStudio[]; code: { id: string; name: string; blurb: string; href: string }[]; recommended_connectors: Connector[] };
export type CopilotRecipe = {
  blueprint_id: string; name: string; category: string; overview: string; description: string; instructions: string;
  knowledge: { dataset: string; guidance: string }[]; tools: { kind: string; name: string; why: string; how: string; url: string; docs: string }[];
  orchestration: string; triggers: { name: string; when: string }[]; topics: { name: string; purpose: string }[];
  workflow: { step: string; kind: string; node: string; how: string; docs: string }[]; review: string[]; evaluation: string;
  samples: { name: string; input: Record<string, unknown> }[]; links: Record<string, string>; markdown: string;
};

export type FrameworkInfo = { id: string; name: string; install: string; docs: string; license: string; hosted: string; language: string };
export type CloudCli = { name: string; install: { os: string; cmd: string }[]; install_docs: string; login: string[]; login_note: string; verify: string[]; login_docs: string };
export type CloudInfo = {
  id: string; name: string; runtime: string; pricing: string; pricing_url: string; docs: string; prereq: string;
  vendor: string; portal_url: string; portal_label: string; account_url: string; cli: CloudCli; roles: string; roles_url: string;
  frameworks: Record<string, string>; frameworks_note: string; samples_url: string; native_providers: string[]; native_note: string; models_url: string;
  model_lookup: string[]; quickstart_url: string; reference_url: string;
};
export type GuideStep = { number: number; title: string; body: string; commands: string[]; links: { label: string; href: string }[] };
export type CloudGuide = {
  cloud: string; cloud_name: string; blueprint_id: string; blueprint_name: string; framework: string; framework_name: string; framework_fit: string; framework_note: string;
  model: string; mode: "gateway" | "native"; mode_note: string; model_fit: { native: boolean; provider: string; note: string }; cost: string; steps: GuideStep[]; filename: string; markdown: string;
};
export type SelfHosting = { title: string; intro: string; steps: Omit<GuideStep, "number">[]; cost: string; docs: string };
export type CustomAgent = { id: string; name: string; description: string; instructions: string; knowledge: string[]; tools: string[]; skills: string[]; builtin_tools?: string[]; starters: string[]; published: boolean; owner_id: string; created_at: string };
export type BuiltinTool = { id: string; description: string; blurb: string; parameters: Record<string, unknown> };
export type FlavorRun = { mode: "smoke" | "live"; ok: boolean; stdout: string; stderr: string; exit_code: number; installed: boolean; ms: number };

export type Connector = {
  id: string; title: string; description: string; version: string; publisher: string; category: string;
  transport: string; remote_url: string; package: { registry: string; identifier: string; version: string; transport: string } | null;
  env_vars: string[]; repo_url: string; website: string; status: string; approval: "pending" | "approved" | "blocked";
  approved_by: string | null; approval_note: string; signals: number; registry_updated_at: string; install: Record<string, unknown>;
};
export type ClientConfig = { client: string; name: string; format: "json" | "bash" | "text"; file: string; snippet: string; steps: string[]; docs: string };
export type Directory = { name: string; url: string; blurb: string };
export type Repo = { id: string; full_name: string; name: string; category: string; blurb: string; relation: string; playground_href: string; url: string; homepage: string; stars: number; forks: number; license: string; language: string; pushed_at: string; topics: string[]; archived: boolean };
export type RepoCategory = { id: string; count: number; blurb: string };
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

export type ShowcaseItemRecord = { id: string; owner_id: string; owner_name: string; owner_department: string; kind: "agent" | "run" | "conversation" | "suite"; ref_id: string; title: string; summary: string; tags: string[]; outcome: string; likes: number; views: number; created_at: string; link: string; liked: boolean; comments?: { id: string; user_id: string; user_name: string; body: string; created_at: string }[] };
export type ShowcaseDraft = { title: string; summary: string; outcome: string; tags: string[]; source: string };
export type ChallengeSubmissionRecord = { id: string; user_id: string; user_name: string; department: string; agent_id: string; agent_name: string; note: string; score: number | null; judged: { avg_score: number | null; pass_rate: number | null; cost_usd: number | null; p95_ms: number | null; cases: number | null } | null; eval_run_id: string | null; rank: number | null; created_at: string };
export type ChallengeRecord = { id: string; owner_id: string; owner_name: string; title: string; brief: string; cases: { input: Record<string, unknown>; expect?: Record<string, unknown> }[]; rubric: EvalRubric; badge: string; status: "open" | "closed"; ends_at: string | null; time_left_h: number | null; winner_submission_id: string | null; created_at: string; submission_count: number; submissions: ChallengeSubmissionRecord[]; judged_now?: number };
export type AchievementRecord = { key: string; name: string; description: string; target: number; icon: string; progress: number; unlocked: boolean; unlocked_at: string | null };
export type CommunityMe = { achievements: AchievementRecord[]; unlocked: number; total: number; rank: number | null; points: number; people: number };
export type LeaderboardRow = { rank: number; user_id?: string; name?: string; department: string; role?: string; people?: number; requests: number; cost_usd: number; savings_usd: number; outcomes: number; agents: number; suites: number; likes: number; achievements: number; challenge_wins: number; pass_rate: number | null; points: number };
export type AdoptionFeature = { feature: string; label: string; hours: number; outcomes: number; cost_usd: number; requests: number; users: number; cost_per_outcome_usd: number | null; minutes_saved_per_outcome: number; hours_saved: number; value_saved_usd: number };
export type AdoptionDepartment = { department: string; users: number; hours: number; outcomes: number; cost_usd: number; hours_saved: number; value_saved_usd: number; roi: number | null };
export type AdoptionAssumption = { key: string; value: number; label: string; updated_at: string };
export type AdoptionSummary = { days: number; department: string | null; since: string; kpis: { active_users: number; total_users: number; hours: number; outcomes: number; cost_usd: number; cost_per_outcome_usd: number | null; hours_saved: number; value_saved_usd: number; roi: number | null }; features: AdoptionFeature[]; departments: AdoptionDepartment[]; weekly: { week: string; requests: number; cost_usd: number; users: number }[]; assumptions: AdoptionAssumption[]; method: string };
