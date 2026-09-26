# Agents: create one, give it tools, run it, take it to your SDK

This guide covers the three ways to get an agent in the playground and how each one runs for real.

## 1. Run a blueprint

Build → Agent Hub lists every runnable blueprint: the six domain blueprints, the platform agents and your wizard agents. Pick a sample input, start the run, and watch the run viewer or the control room. Runs are checkpointed, so a review gate can wait for hours and resume where it stopped. Every model call is metered to you and appears in Traces.

**Platform agents** run the playground itself. As of Batch 14 there are six: Adoption digest, Showcase writer, Key health check (probes every platform key and raises an alert for any provider that rejects it), Cost sentinel (compares the last day's spend per department and feature with the trailing week and alerts on jumps), Connector reviewer (prepares the MCP approval queue with approve, hold or block recommendations) and Onboarding coach (reads a person's ledger and suggests their next three steps).

## 2. Build one in the wizard

Create your own agent asks for the same things Copilot Studio does: name, description, instructions, knowledge (Knowledge Spaces), skills, tools and starter prompts, plus publishing.

**Tools** come from two places:

| Kind | What it is | Where it runs |
| --- | --- | --- |
| Built-in tools | `current_date`, `calculate` (exact arithmetic), `query_dataset` (rows from the mock datasets with equality filters), `search_knowledge` (hybrid search over your Knowledge Spaces), `fetch_url` (public HTTPS pages only; private and local addresses are blocked), `run_python` (a 20-second snippet in your sandbox) | Inside the API with your identity |
| Connectors | Any admin-approved MCP server from the marketplace | The server, called through the playground's MCP client |

The agent runs on the prompt-agent graph: prepare (retrieve knowledge, attach skills and tools), respond (the model may request tool calls), tools (the playground executes them and the model finishes with the results), check (citations and problems). Tool calls and their results are part of the run output.

The wizard agent exports as a Microsoft 365 declarative agent manifest, and the Low-code studios page turns any blueprint into a Langflow flow, an n8n workflow or a Copilot Studio recipe.

## 3. Bring your own SDK through the gateway

The playground exposes an OpenAI-compatible gateway at `/openai/v1`. Any SDK that speaks the Chat Completions API works: the OpenAI SDK, OpenAI Agents SDK, LangChain and LangGraph, CrewAI, Microsoft Agent Framework, Google ADK through LiteLLM, and anything else with a `base_url` setting.

```bash
export PLAYGROUND_BASE_URL=http://localhost:8000/openai/v1   # the playground API
export PLAYGROUND_TOKEN=pgk_...                              # Admin → Settings → Personal tokens
export PLAYGROUND_MODEL=smart                                # or any catalog id
```

```python
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["PLAYGROUND_BASE_URL"], api_key=os.environ["PLAYGROUND_TOKEN"])
client.chat.completions.create(model="smart", messages=[{"role": "user", "content": "Hello"}], extra_headers={"X-Trace-Id": "my-session"})
```

What the gateway does with every call: resolves `smart` through Smart routing, applies your role policy and budget, uses your personal key or the platform key for the provider, meters the call as feature `sdk` with the key source, and groups calls that share an `X-Trace-Id` header (or `metadata.trace_id`) into one trace. Streaming, tool calls (`tools` in, `tool_calls` out) and content parts are supported; errors come back in the OpenAI error shape with 401, 402, 403, 404 or 502.

`GET /openai/v1/models` lists `smart` plus every model you may use.

### Framework projects that run

Discover → Frameworks renders any blueprint as a project for the OpenAI Agents SDK, LangGraph, CrewAI, Microsoft Agent Framework or Google ADK. Since Batch 14 every project points at the gateway, so it needs no provider key. Two buttons run it in your sandbox:

- **Run smoke test** executes the project's offline test (the module parses, the tool stubs are wired).
- **Run live in sandbox** installs the framework into your sandbox environment (once), mints a short-lived personal token, runs `agent.py` through the gateway, and removes the token. The calls appear in Traces under `sandbox-<framework>`. Google ADK projects are interactive (`adk run`), so they run locally after download.

## Traces

Operate → Traces lists runs, SDK sessions and chats. A run's timeline shows each step beside the model calls it made, with model, tokens, cost, latency and which key paid; an SDK session groups gateway calls by trace id; a chat shows messages and calls. Admins and champions see the organisation; everyone else sees their own.

## How-to panels

Every major page has a floating **How to** button with the steps for that page and links to the vendor documentation. Dismissing it remembers the choice in that browser.
