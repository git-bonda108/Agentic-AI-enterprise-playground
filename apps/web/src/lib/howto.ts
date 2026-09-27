/** Contextual "How to" guidance per page: numbered steps with the exact place to click, and where to read more. */

export type HowToStep = { text: string; href?: string; label?: string };
export type HowTo = { title: string; intro: string; steps: HowToStep[]; docs: { label: string; href: string }[] };

const DOCS = "/docs";

export const HOWTO: Record<string, HowTo> = {
  "/build/agents": {
    title: "Create an agent, add tools, run it",
    intro: "Three ways to get an agent: run a blueprint, build one in the wizard, or bring your own SDK through the gateway.",
    steps: [
      { text: "Run a blueprint with a sample input; review gates pause it until you approve or reject in the review inbox." },
      { text: "Create your own agent: instructions, Knowledge Spaces, skills, built-in tools (calculator, datasets, knowledge search, web fetch, sandboxed Python) and approved MCP connectors." },
      { text: "Watch a run in the run viewer or the control room; every step, token and dollar is recorded.", href: "/operate/runs", label: "Runs" },
      { text: "Take it further: the same blueprint as a notebook, a framework project, a Langflow flow or a Copilot Studio recipe.", href: "/discover/low-code", label: "Two ways to build" },
    ],
    docs: [{ label: "Agents guide", href: `${DOCS}/agents` }, { label: "Copilot Studio agents", href: "https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-get-started" }],
  },
  "/discover/frameworks": {
    title: "Run your own SDK through the playground",
    intro: "Every project points at the OpenAI-compatible gateway, so it needs no provider key and stays governed and metered.",
    steps: [
      { text: "Pick a framework and a blueprint; read agent.py, then run the offline smoke test in the sandbox." },
      { text: "Run live: the sandbox installs the SDK and executes agent.py through the gateway with a short-lived token; the calls appear in Traces.", href: "/operate/traces", label: "Traces" },
      { text: "Download the project. Set PLAYGROUND_BASE_URL, PLAYGROUND_TOKEN (Admin → Settings → Personal tokens) and PLAYGROUND_MODEL, then python agent.py." },
      { text: "Deploy it when it behaves: pick a cloud platform and follow the step-by-step guide.", href: "/discover/clouds", label: "Cloud platforms" },
    ],
    docs: [{ label: "OpenAI Agents SDK", href: "https://openai.github.io/openai-agents-python/" }, { label: "LangGraph", href: "https://docs.langchain.com/oss/python/langgraph/overview" }, { label: "CrewAI", href: "https://docs.crewai.com/en/quickstart" }, { label: "Microsoft Agent Framework", href: "https://learn.microsoft.com/en-us/agent-framework/overview" }, { label: "Google ADK", href: "https://adk.dev/get-started/python/" }],
  },
  "/discover/clouds": {
    title: "Take an agent to a cloud runtime",
    intro: "Four runtimes, one path: sign in to the portal, sign in with the CLI, run the project once locally, choose where the model lives, then scaffold, test, deploy and invoke.",
    steps: [
      { text: "Pick the platform: the card shows the runtime, the pricing unit and what you need before you start; Open portal and the CLI sign-in commands are right there." },
      { text: "Build the guide: blueprint, framework, model and model mode. Gateway keeps the agent governed and metered by the playground; native bills the cloud account." },
      { text: "Copy each step's commands in order, or download the whole guide as markdown for a ticket or a runbook." },
      { text: "Prefer a one-shot script? The deploy script below the guide is the short form for the same cloud.", href: "/discover/frameworks", label: "Frameworks" },
    ],
    docs: [{ label: "Cloud platforms guide", href: `${DOCS}/cloud-platforms` }, { label: "Foundry hosted agents", href: "https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-hosted-agent" }, { label: "AgentCore CLI", href: "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html" }, { label: "Agent Runtime", href: "https://adk.dev/deploy/agent-runtime/deploy/" }, { label: "Managed Agents", href: "https://platform.claude.com/docs/en/managed-agents/quickstart" }],
  },
  "/build/data": {
    title: "Pick a dataset, then bring real data",
    intro: "Every mock set is synthetic, deterministic and safe to run any blueprint against; each card shows its columns, what it is modelled on and who reads it.",
    steps: [
      { text: "Read the columns and the preview, download the set as CSV or JSON, or copy the two-line notebook snippet." },
      { text: "Open the linked notebook to see the set in use with pandas or a Knowledge Space.", href: "/build/notebooks", label: "Notebooks" },
      { text: "Trusted sources: Kaggle, Hugging Face, UCI, OpenML, Data.gov and more, each with the loader it publishes; run the %pip line in the sandbox, then the snippet." },
    ],
    docs: [{ label: "Datasets guide", href: `${DOCS}/datasets` }, { label: "Kaggle API", href: "https://www.kaggle.com/docs/api" }, { label: "Hugging Face Datasets", href: "https://huggingface.co/docs/datasets/index" }],
  },
  "/operate/cost": {
    title: "Drill from the organisation to one call",
    intro: "Every number reconciles to the same ledger rows. Click a row to filter by it and move one layer down; the chips at the top show where you are.",
    steps: [
      { text: "Pick a window, then a layer: department, user, feature, model, provider, key source, blueprint or conversation." },
      { text: "Click a row to add it as a filter; the next layer opens already narrowed. Remove a chip to widen again." },
      { text: "The ledger rows at the bottom are the raw calls behind the view, newest first; export any view or the rows as CSV." },
      { text: "Tokens are split into input, output and cached so prompt caching shows up as savings.", href: "/operate/traces", label: "Traces" },
    ],
    docs: [{ label: "API: usage", href: `${DOCS}/api` }],
  },
  "/build/notebooks": {
    title: "Run a notebook end to end",
    intro: "Every notebook starts with the playground helper and runs on mock data with your key.",
    steps: [
      { text: "Open a notebook from the gallery, or run it in the sandbox to see every cell's output at once." },
      { text: "Edit the payload cell and run again; use %pip install for packages in the sandbox." },
      { text: "Take it to GPU compute with More compute (NVIDIA Brev, Colab, Codespaces)." },
    ],
    docs: [{ label: "Notebooks guide", href: `${DOCS}/notebooks` }],
  },
  "/discover/low-code": {
    title: "Build it in a studio",
    intro: "Pick a blueprint and a studio; download the artefact; follow the five steps.",
    steps: [
      { text: "Langflow: upload the flow JSON, set the model key, paste a personal token into the MCP Tools headers." },
      { text: "n8n: paste the workflow JSON, add the model credential and a Bearer credential for the playground." },
      { text: "Copilot Studio: paste the instructions, add the knowledge and tools the recipe lists, build the workflow with the node map." },
    ],
    docs: [{ label: "Two ways to build", href: `${DOCS}/low-code` }],
  },
  "/discover/connectors": {
    title: "Connect a server to your client",
    intro: "Open a tile, pick your client, copy the configuration, add the secret it names.",
    steps: [
      { text: "The playground's own server is the first featured tile: create a personal token in Settings and paste it in place of the placeholder." },
      { text: "Admins approve servers before agents can call them; the Connector reviewer agent prepares the queue.", href: "/build/agents", label: "Agent Hub" },
      { text: "Test connection shows the server's tools before you commit to it." },
    ],
    docs: [{ label: "Marketplace guide", href: `${DOCS}/marketplace` }],
  },
  "/discover/blueprints": {
    title: "Find the right blueprint",
    intro: "Gen AI blueprints are one model call with instructions and knowledge; Agentic AI blueprints have steps, tools and review.",
    steps: [
      { text: "Filter by category and family; open a card for the instructions and the build tracks." },
      { text: "Run it, open it as a notebook, take the code, or build it in a low-code studio." },
    ],
    docs: [{ label: "Architecture", href: `${DOCS}/architecture` }],
  },
  "/build/knowledge": {
    title: "Give agents your documents",
    intro: "A Knowledge Space holds documents, URLs, datasets or a repository map; agents and notebooks search it.",
    steps: [
      { text: "Create a space, add text or files, then search it and ask it a question with citations." },
      { text: "Attach the space to a wizard agent, or use the search_knowledge built-in tool from any agent." },
    ],
    docs: [{ label: "API reference", href: `${DOCS}/api` }],
  },
  "/evaluate/evals": {
    title: "Prove an agent before people rely on it",
    intro: "Golden cases, a judge, gates and a nightly canary that can roll a wizard agent back.",
    steps: [
      { text: "Build a suite from a good run with the five-step builder; set the gate thresholds." },
      { text: "Run it, read the judge's rationale per case, enable the canary." },
      { text: "Watch the hardening ladder; promote to Production when three canaries pass." },
    ],
    docs: [{ label: "Workflows", href: `${DOCS}/workflows` }],
  },
  "/operate/traces": {
    title: "Read a trace",
    intro: "Runs, SDK sessions and chats as timelines of steps and metered calls.",
    steps: [
      { text: "Open a trace to see each step next to the model calls it made: model, tokens, cost, latency, key source." },
      { text: "SDK sessions come from the gateway; send an X-Trace-Id header from your code to group calls." },
    ],
    docs: [{ label: "Agents guide", href: `${DOCS}/agents` }],
  },
};

export function howtoFor(pathname: string): HowTo | null {
  const key = Object.keys(HOWTO).find((k) => pathname === k || pathname.startsWith(k + "/"));
  return key ? HOWTO[key] : null;
}
