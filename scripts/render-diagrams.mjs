// Renders the architecture, workflow, deployment and run-flow diagrams to docs/images/*.png in the playground palette.
// Uses the Playwright Chromium already installed for the end-to-end tests and Mermaid from a CDN.
//   npm run diagrams
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const OUT = resolve("docs/images");
mkdirSync(OUT, { recursive: true });

const theme = {
  theme: "base",
  themeVariables: {
    background: "#0A0A14", primaryColor: "#1a1330", primaryTextColor: "#ECECF4", primaryBorderColor: "#8B5CF6", lineColor: "#06B6D4",
    secondaryColor: "#12121A", tertiaryColor: "#1b1024", noteBkgColor: "#12121A", noteTextColor: "#ECECF4", noteBorderColor: "#EC4899",
    edgeLabelBackground: "#12121A", clusterBkg: "#12121A", clusterBorder: "#2a2a3a", fontFamily: "Inter, ui-sans-serif, system-ui", fontSize: "14px",
    actorBkg: "#1a1330", actorBorder: "#8B5CF6", actorTextColor: "#ECECF4", signalColor: "#06B6D4", signalTextColor: "#ECECF4", labelBoxBkgColor: "#1b1024", labelBoxBorderColor: "#EC4899", labelTextColor: "#ECECF4", loopTextColor: "#ECECF4", activationBkgColor: "#2a1a4a", activationBorderColor: "#8B5CF6", sequenceNumberColor: "#0A0A14",
  },
};

const diagrams = {
  architecture: `flowchart LR
  U["Employees<br/>browser"] -->|"HTTPS · Entra ID session"| W["Web app<br/>Next.js 16"]
  W -->|"internal key + identity headers"| A["API<br/>FastAPI · LangGraph · LiteLLM"]
  A --> P[("Model providers<br/>Anthropic · OpenAI · Azure OpenAI<br/>Google · DeepSeek · Hugging Face")]
  A --> DB[("Postgres + pgvector<br/>ledger · runs · knowledge · evals")]
  A --> CK[("Checkpoints")]
  A -->|"notebook code"| S["Container Apps<br/>dynamic sessions"]
  A -->|"MCP client"| M["MCP servers<br/>official registry"]
  X["Claude Desktop · Cursor · VS Code"] -->|"MCP · personal token"| A
  W --> J["JupyterLite<br/>in the browser"]
  ID["Microsoft Entra ID"] -.->|"OIDC"| W
  KV["Key Vault"] -.->|"provider keys"| A`,
  workflow: `flowchart LR
  subgraph Explore
    D["Discover<br/>models · blueprints · connectors · skills"] --> PG["Playground<br/>chat · compare · Smart routing"]
  end
  subgraph Build
    PG --> R["Run a blueprint<br/>graph · review gate"]
    R --> N["Notebook · code · deploy<br/>five frameworks · four clouds"]
    R --> K["Knowledge Spaces<br/>documents · repositories"]
    W["Wizard agent<br/>knowledge · skills · connectors"] --> R
  end
  subgraph Evaluate
    R --> E["Suite<br/>checks · rubric · gate"]
    E --> C["Nightly canary<br/>drift · rollback"]
    C --> H["Hardening ladder<br/>Draft to Production"]
  end
  subgraph Operate
    R --> L["Ledger<br/>tokens · cost · savings"]
    L --> CO["Cost cockpit · Adoption<br/>hours · outcomes · ROI"]
    E --> CM["Community<br/>showcase · challenges · leaderboard"]
  end`,
  deployment: `flowchart TB
  FD["Azure Front Door<br/>WAF · TLS · optional"] --> WEB
  subgraph ACA["Azure Container Apps environment"]
    WEB["web<br/>Next.js standalone"] --> API["api<br/>FastAPI · internal ingress"]
    SESS["Dynamic sessions pool<br/>notebook sandbox"]
  end
  API --> PG[("Azure Database for PostgreSQL<br/>Flexible Server + pgvector")]
  API --> REDIS[("Azure Cache for Redis")]
  API --> SESS
  API -.->|"secrets"| KV["Key Vault"]
  WEB -.->|"OIDC"| ENTRA["Microsoft Entra ID"]
  ACR["Container Registry<br/>images from CI"] -.-> WEB
  ACR -.-> API
  WEB & API -.->|"logs · metrics"| MON["Log Analytics"]`,
  runflow: `sequenceDiagram
  participant B as Browser
  participant A as API
  participant G as LangGraph
  participant P as Provider
  B->>A: POST /v1/runs (blueprint, input)
  A->>A: policy check · budget check
  A->>G: invoke on a background thread
  G->>P: metered model call (Workhorse tier)
  P-->>G: text · usage
  G->>A: checkpoint after each node
  G-->>A: interrupt: review needed
  A-->>B: waiting_review
  B->>A: POST /v1/runs/{id}/resume (decision)
  A->>G: resume from checkpoint
  G-->>A: completed · output
  A-->>B: run · ledger rows · savings`,
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#0A0A14;font-family:Inter,ui-sans-serif,system-ui}#host{display:inline-block;padding:40px}</style></head><body><div id="host"></div><script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"; window.mermaid = mermaid; mermaid.initialize(${JSON.stringify({ startOnLoad: false, ...theme })});</script></body></html>`);
await page.waitForFunction(() => Boolean(window.mermaid));
for (const [name, code] of Object.entries(diagrams)) {
  await page.evaluate(async ({ code, name }) => {
    const { svg } = await window.mermaid.render(`d-${name}`, code);
    document.getElementById("host").innerHTML = svg;
  }, { code, name });
  await page.locator("#host").screenshot({ path: `${OUT}/${name}.png` });
  console.log(`rendered ${name}.png`);
}
await browser.close();
