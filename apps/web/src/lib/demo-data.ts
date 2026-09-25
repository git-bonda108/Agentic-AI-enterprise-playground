/** Seeded console data for Batch 0. The usage ledger replaces it in Batch 1. */

export const STATS = {
  credits: 2_500,
  spendMonth: 312.4,
  spendLimit: 5_000,
  tokens7d: 4_180_000,
  tokensDelta: 0.18,
  cacheReuse: 0.42,
  activeUsers: 8,
};

export const TOKEN_SERIES = [
  { day: "Fri", tokens: 410 }, { day: "Sat", tokens: 180 }, { day: "Sun", tokens: 120 },
  { day: "Mon", tokens: 690 }, { day: "Tue", tokens: 820 }, { day: "Wed", tokens: 960 }, { day: "Thu", tokens: 1000 },
];

export type ModelCard = {
  id: string;
  name: string;
  provider: string;
  tier: "Frontier" | "Premium" | "Workhorse" | "Economy";
  tags: string[];
  input: number;
  output: number;
  art: string;
  isNew?: boolean;
};

export const MODELS: ModelCard[] = [
  { id: "claude-fable-5-1", name: "Fable 5.1", provider: "Anthropic", tier: "Frontier", tags: ["Most capable", "Research", "Multi-day tasks"], input: 10, output: 50, art: "linear-gradient(135deg,#5b8def,#7c3aed)" },
  { id: "claude-opus-5-5", name: "Opus 5.5", provider: "Anthropic", tier: "Premium", tags: ["Complex projects", "Agents", "Coding"], input: 4, output: 20, art: "linear-gradient(135deg,#f0865f,#ec4899)", isNew: true },
  { id: "gpt-5-6-terra", name: "GPT-5.6 Terra", provider: "Azure OpenAI", tier: "Workhorse", tags: ["Everyday tasks", "Tool use"], input: 2, output: 12, art: "linear-gradient(135deg,#0ea5e9,#06b6d4)" },
  { id: "claude-sonnet-5", name: "Sonnet 5", provider: "Anthropic", tier: "Workhorse", tags: ["Writing", "Cost-efficient"], input: 2, output: 10, art: "linear-gradient(135deg,#e7e2d6,#c9c2b3)" },
  { id: "deepseek-v4-flash", name: "DeepSeek V4 Flash", provider: "Foundry", tier: "Economy", tags: ["High volume", "Lowest cost"], input: 0.14, output: 0.28, art: "linear-gradient(135deg,#34d399,#0d9488)" },
  { id: "claude-haiku-4-5", name: "Haiku 4.5", provider: "Anthropic", tier: "Economy", tags: ["Fastest", "Classification"], input: 1, output: 5, art: "linear-gradient(135deg,#a7c4bc,#6b9080)" },
];

export type BlueprintCard = {
  id: string;
  name: string;
  family: "Domain" | "Role" | "Topology" | "Persona" | "Low-code" | "Cloud";
  pattern: string;
  summary: string;
  flavors: string[];
  batch: number;
};

export const BLUEPRINTS: BlueprintCard[] = [
  { id: "doc-reconciliation", name: "Document reconciliation", family: "Domain", pattern: "Supervisor–worker, parallel validation", summary: "Extract, cross-check and escalate invoices, contracts and POs with confidence gates.", flavors: ["LangGraph", "Agents SDK", "CrewAI"], batch: 3 },
  { id: "sage-lens", name: "Sage Lens deep research", family: "Domain", pattern: "Clarity → research → validate → synthesize", summary: "Sourced research with a validator loop and human clarification when the ask is vague.", flavors: ["LangGraph", "ADK", "Claude"], batch: 3 },
  { id: "learning-path", name: "Learning path generator", family: "Domain", pattern: "Generator–critic", summary: "Three-level competency paths per role with curated references.", flavors: ["Agents SDK", "Agent Framework"], batch: 3 },
  { id: "review-panel", name: "Review panel", family: "Domain", pattern: "Five-critic panel", summary: "Any draft, reviewed for legal, consistency, completeness and alignment before it ships.", flavors: ["Agent Framework", "CrewAI"], batch: 3 },
  { id: "data-analyst", name: "Data analyst", family: "Domain", pattern: "Deterministic router → specialists", summary: "Natural-language questions into statistics, queries and charts over CSV or Excel.", flavors: ["Agents SDK", "LangGraph"], batch: 3 },
  { id: "knowledge-qa", name: "Knowledge Q&A", family: "Domain", pattern: "Conversational retrieval", summary: "Grounded answers with citations over your Knowledge Spaces.", flavors: ["LangGraph", "ADK", "Strands"], batch: 3 },
];

export const RESOURCES = [
  { title: "Playground", body: "Chat with any model, compare four side by side, copy the request as code.", href: "/build/playground", batch: 1 },
  { title: "Notebooks", body: "Open any run as a notebook in the browser or a sandboxed Python session.", href: "/build/notebooks", batch: 5 },
  { title: "Connectors", body: "Attach approved MCP servers such as SharePoint, Jira, GitHub and Postgres.", href: "/discover/connectors", batch: 6 },
  { title: "Evaluate", body: "Turn on evaluation and let the wizard explain rubrics, metrics and gates.", href: "/evaluate/evals", batch: 7 },
];
