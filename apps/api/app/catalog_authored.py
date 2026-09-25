"""Authored catalog entries: Copilot Studio style low-code templates and mirrors of cloud provider samples."""

from __future__ import annotations


def _lowcode(id_: str, name: str, summary: str, instructions: str, knowledge: list[str], prompts: list[str]) -> dict:
    return {
        "id": f"lowcode-{id_}", "name": name, "family": "Low-code", "group": "template",
        "source": {"repo": "playground", "path": f"lowcode/{id_}", "license": "MIT", "url": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/template-fundamentals", "title": "Playground templates"},
        "summary": summary, "instructions": instructions, "instructions_truncated": False, "tools": ["knowledge"] if knowledge else [],
        "model_hint": "", "tags": ["no-code", "copilot-studio-style"], "runnable": True, "tier": "Economy",
        "knowledge": knowledge, "starter_prompts": prompts, "flavors": ["No-code", "Copilot Studio export"],
        "samples": [{"name": p[:48], "input": {"task": p}} for p in prompts[:3]],
        "links": {"pattern": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-first-bot"},
    }


LOWCODE_TEMPLATES: list[dict] = [
    _lowcode("it-helpdesk", "IT helpdesk", "Answers common IT questions and collects the details for a ticket.", "You are the IT helpdesk agent. Answer common questions about passwords, devices, VPN and email from the policies you are given. When you cannot resolve an issue, collect device, error message and urgency and draft a ticket summary.", ["policies"], ["My laptop will not connect to the VPN, what do I check?", "How often must I rotate my password?", "Draft a ticket: printer on floor 3 is offline"]),
    _lowcode("website-qa", "Website Q&A", "Answers questions from a set of pages or documents with citations.", "You answer questions strictly from the documents provided and cite them. If the answer is not in the documents, say so and suggest who to ask.", ["policies"], ["What is the expense limit for hotels?", "Where do I find the procurement thresholds?"]),
    _lowcode("benefits", "Benefits assistant", "Explains employee benefits and learning budgets.", "You explain employee benefits, learning budgets and reimbursement rules from the policies provided, in plain language, and always name the policy you relied on.", ["policies"], ["How much is my learning budget this year?", "Are certifications reimbursed?"]),
    _lowcode("plan-my-day", "Plan my day", "Turns a list of tasks and meetings into a prioritized plan.", "You are a planning assistant. Given tasks, meetings and deadlines, produce a prioritized plan for the day with time blocks, flag conflicts, and suggest what to defer.", [], ["Tasks: finish the budget deck, review two invoices, 1:1 at 2pm, gym at 6. Plan my day."]),
    _lowcode("know-my-customer", "Know my customer", "Prepares a customer briefing from notes you paste in.", "You prepare concise customer briefings: company snapshot, recent interactions, open issues, and three talking points. Use only the notes provided; never invent facts.", [], ["Notes: Contoso, 3 open invoices, complained about delivery delays in March, renewal in June. Brief me."]),
    _lowcode("executive-briefing", "Executive briefing", "Condenses updates into a one-page executive briefing.", "You write one-page executive briefings: headline, three key points, risks, decisions needed. Keep it under 250 words.", [], ["Summarize: the AI playground pilot has 8 users, spend is $12, two agents are in production, the vendor keys need renewal."]),
    _lowcode("company-policy", "My company policy", "Answers policy questions with citations.", "You answer policy questions using only the policies provided and cite the policy id. Flag when a request needs a manager or HR approval.", ["policies"], ["Can I work from Spain for two months?", "What approvals does a 30,000 USD purchase need?"]),
    _lowcode("request-tracker", "Request tracker", "Turns free text into a structured request record.", "You convert free-text requests into a structured record: requester, type, priority, due date, summary, next step. Ask for missing fields.", [], ["I need a new monitor for the design team by Friday, medium priority."]),
    _lowcode("ai-learning-advisor", "AI learning advisor", "Recommends learning paths for AI skills by role.", "You recommend learning steps for AI skills tailored to the person's role and current level, with one practical exercise per step.", ["learning_refs"], ["I am a finance analyst who has never used AI tools. Where do I start?"]),
    _lowcode("status-update", "Status update agent", "Writes a status update from raw notes.", "You write crisp status updates: done, in progress, blocked, next week. Keep each bullet to one line.", [], ["Notes: shipped playground batch 3, evals next, blocked on OpenAI key, demo on Thursday."]),
    _lowcode("sme-finder", "SME finder", "Suggests who to ask based on a directory you provide.", "Given a question and a directory of people with skills, suggest the two best people to ask and why. If nobody fits, say so.", [], ["Who should I ask about invoice matching tolerances? Directory: Priya (training), Daniel (finance ops), Mei (engineering)."]),
    _lowcode("project-digest", "Project delta digest", "Summarizes what changed in a project since last week.", "You produce a delta digest: what changed, what slipped, new risks, decisions made. Use only the notes given.", [], ["Last week: 3 features done, 1 slipped to next sprint, new risk: vendor key expiry."]),
    _lowcode("news-digest", "Personal news digest", "Summarizes pasted articles into a personal digest.", "You summarize pasted articles into a digest with one line per item and a why-it-matters note for the reader's role.", [], ["Role: procurement lead. Articles: tariff change on steel; new supplier onboarding rules; AI in contract review."]),
    _lowcode("safe-travels", "Safe travels", "Answers travel policy and safety questions.", "You answer travel policy questions from the policies provided and add practical safety reminders. Cite the policy.", ["policies"], ["I am flying 10 hours to Singapore, can I book business class?"]),
    _lowcode("sustainability", "Sustainability insights", "Explains sustainability metrics in plain terms.", "You explain sustainability and carbon accounting terms in plain language and suggest the next question a manager should ask.", [], ["What is scope 3 and why does procurement care?"]),
    _lowcode("weather-style-faq", "Quick FAQ agent", "A template for any small FAQ, swap in your own knowledge.", "You answer frequently asked questions from the knowledge provided, briefly and politely, and offer the contact for anything else.", ["policies"], ["When do expense claims have to be filed?"]),
]


def _cloud(id_: str, name: str, provider: str, summary: str, url: str, framework: str, deploy_url: str) -> dict:
    return {
        "id": f"cloud-{id_}", "name": name, "family": "Cloud", "group": provider,
        "source": {"repo": url.replace("https://github.com/", "").split("/tree/")[0], "path": url, "license": "Apache-2.0", "url": url, "title": provider},
        "summary": summary, "instructions": f"Mirror of the {provider} sample '{name}'. Open the source to read the code; use Deploy to follow the provider's runtime guide.", "instructions_truncated": False,
        "tools": [], "model_hint": "", "tags": ["cloud", provider.lower().replace(" ", "-"), framework.lower()], "runnable": False, "tier": "Workhorse",
        "flavors": [framework], "links": {"deploy": deploy_url},
    }


AGENTCORE = "https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/02-use-cases/"
ADK = "https://github.com/google/adk-samples/tree/main/python/agents/"
CLOUD_MIRRORS: list[dict] = [
    _cloud("agentcore-customer-support", "Customer support agent", "AWS AgentCore", "End-to-end customer support agent with memory and gateway tools.", "https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/05-blueprints/customer-support-agent-with-agentcore", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-toolkit.html"),
    _cloud("agentcore-sre", "SRE agent", "AWS AgentCore", "Incident triage agent over operational data.", AGENTCORE + "SRE-agent", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html"),
    _cloud("agentcore-deep-research", "Deep research agent", "AWS AgentCore", "Long-running research with the Harness and Code Interpreter.", AGENTCORE + "deep-research-agent", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html"),
    _cloud("agentcore-receipts-idp", "Receipts document processing", "AWS AgentCore", "Intelligent document processing for receipts with human review.", AGENTCORE + "receipts-intelligent-document-processing-agent", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html"),
    _cloud("agentcore-it-incident", "IT incident response", "AWS AgentCore", "Event-driven incident response workflow.", AGENTCORE + "it-incident-response-agent", "LangGraph", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html"),
    _cloud("agentcore-finance-assistant", "Finance personal assistant", "AWS AgentCore", "Conversational finance assistant with memory.", AGENTCORE + "finance-personal-assistant", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html"),
    _cloud("agentcore-data-analyst", "Data analyst conversational assistant", "AWS AgentCore", "Natural-language analytics over a data platform.", AGENTCORE + "data-analyst-conversational-assistant", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-tool.html"),
    _cloud("agentcore-multitenant", "Multi-tenant agentic platform", "AWS AgentCore", "Blueprint for a governed multi-tenant agent platform.", "https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/05-blueprints/multitenant-agentic-platform", "Strands", "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html"),
    _cloud("adk-financial-advisor", "Financial advisor", "Google ADK", "Multi-agent financial planning sample.", ADK + "financial-advisor", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-data-science", "Data science agent", "Google ADK", "Data science workflow with BigQuery and code execution.", ADK + "data-science", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-deep-search", "Deep search", "Google ADK", "Iterative research with search grounding.", ADK + "deep-search", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-llm-auditor", "LLM auditor", "Google ADK", "Critic and reviser pair that audits model answers.", ADK + "llm-auditor", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-software-bug-assistant", "Software bug assistant", "Google ADK", "Triage assistant over a bug tracker with MCP tools.", ADK + "software-bug-assistant", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-document-analyzer", "High-volume document analyzer", "Google ADK", "Parallel document analysis at scale.", ADK + "high-volume-document-analyzer", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-travel-concierge", "Travel concierge", "Google ADK", "Multi-agent trip planning with tools.", ADK + "travel-concierge", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("adk-sdlc-planner", "SDLC task planner", "Google ADK", "Plans software delivery tasks from requirements.", ADK + "sdlc-task-planner", "Google ADK", "https://adk.dev/deploy/"),
    _cloud("foundry-competitive-researcher", "Competitive landscape researcher", "Microsoft Foundry", "Starter agent manifest from the Foundry agent catalog.", "https://ai.azure.com/catalog/agents", "Agent Framework", "https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent"),
    _cloud("foundry-prompt-agent", "Prompt agent quickstart", "Microsoft Foundry", "Declarative prompt agent with instructions, tools and knowledge.", "https://github.com/microsoft-foundry/foundry-samples", "Agent Framework", "https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent"),
]
