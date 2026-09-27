# Cloud platforms

Where a blueprint runs once it leaves the playground, how to sign in, and the exact steps to deploy it. The page lives under Discover, Cloud platforms; the routes are `GET /v1/clouds`, `GET /v1/clouds/guide` and `GET /v1/clouds/self-hosting`. Commands follow the official quickstarts as of September 2026 and every step links to the page it came from.

## The four runtimes

| Platform | Runtime | Portal | CLI sign-in | Pricing unit |
| --- | --- | --- | --- | --- |
| Microsoft Foundry | Foundry Agent Service hosted agents (containers built from your source) and prompt agents | [ai.azure.com](https://ai.azure.com) | `azd auth login`, `az login` (Foundry DevPack installs azd, the Foundry extensions and az) | Model tokens at standard rates; hosted agents billed as Container Apps compute |
| AWS Bedrock AgentCore | AgentCore Runtime, session-isolated microVMs, with Memory, Gateway, Identity and Observability | [AgentCore console](https://console.aws.amazon.com/bedrock-agentcore/home) | `aws configure sso`, `aws sso login --profile <profile>`; `npm install -g @aws/agentcore` | $0.1276 per vCPU-hour and $0.0169 per GB-hour on consumption; idle is free |
| Google Cloud Agent Runtime | Agent Runtime on the Agent Platform (formerly Vertex AI Agent Engine) | [Agent Runtime console](https://console.cloud.google.com/vertex-ai/agents/agent-engines) | `gcloud auth login`, `gcloud auth application-default login`, `gcloud config set project`, enable the Agent Platform and Cloud Resource Manager APIs | Per vCPU-hour and GiB-hour while the agent serves, plus Vertex AI token rates |
| Anthropic Managed Agents | Anthropic's hosted harness with cloud or self-hosted sandboxes (beta, header `managed-agents-2026-04-01`) | [Claude Console](https://platform.claude.com) | `export ANTHROPIC_API_KEY=...`; `brew install anthropics/tap/ant` | $0.08 per session-hour while running, plus standard token rates |

## Framework fit

Every framework project from the Frameworks page (OpenAI Agents SDK, LangGraph, CrewAI, Microsoft Agent Framework, Google ADK) can reach every runtime, but not with the same amount of glue. The page labels each pairing:

| Fit | Meaning |
| --- | --- |
| first-class | The runtime's own CLI scaffolds that framework: `azd ai agent init` for Agent Framework, `agentcore create` for LangGraph, ADK and OpenAI Agents, `adk deploy agent_engine` for ADK |
| sample | An official sample shows the wrapper (LangGraph and OpenAI Agents hosted agents on Foundry; the LangGraph template on Agent Runtime) |
| bring your own | The code deploys as a plain container or a custom template class and you write a small adapter (CrewAI and ADK on Foundry; CrewAI and Agent Framework on AgentCore; CrewAI, OpenAI Agents and Agent Framework on Agent Runtime) |
| harness | Managed Agents runs Anthropic's loop: the blueprint's instructions, tools and MCP servers deploy, the framework code does not |

## Two model modes

Every project reads `PLAYGROUND_BASE_URL`, `PLAYGROUND_TOKEN` and `PLAYGROUND_MODEL`, which makes the model choice a deployment decision rather than a code change.

- **Through the playground gateway.** The deployed agent keeps calling the playground's OpenAI-compatible gateway. The role policy, budget, Smart routing, key resolution, metering and Traces still apply, and token spend stays on the playground ledger. The playground must be reachable from the cloud (its deployed URL, never localhost) and the token is stored as a secret of the runtime, never in the source.
- **Native provider endpoint.** The agent calls the cloud's own model and the token spend lands on that cloud bill. The guide checks whether the cloud sells the chosen model's provider: Foundry sells Azure OpenAI, OpenAI, Anthropic, Mistral, Cohere, DeepSeek, xAI, Hugging Face and NVIDIA NIM models; Bedrock serves Anthropic, Mistral, Cohere and DeepSeek, and the AgentCore wizard attaches OpenAI, Anthropic or Gemini API keys; Vertex AI serves Gemini plus Claude, Mistral, DeepSeek and Hugging Face partner models; Managed Agents runs Claude only. If the cloud does not sell the model, the guide says so and falls back to the gateway mode. On Foundry the native switch is three environment variables, because the resource's OpenAI v1 endpoint speaks the same API as the gateway.

Smart routing is a playground feature and only exists in gateway mode.

## The guide

`GET /v1/clouds/guide?blueprint=<id>&cloud=<id>&framework=<id>&model=<id>&mode=gateway|native` returns an ordered guide; `download=1` returns the same guide as markdown with a filename. The steps are always in this order:

1. Sign in to the portal: what to create or copy (project endpoint, region, API key).
2. Install the CLI and sign in: install per operating system, the sign-in commands, a verify command, and the roles the identity needs.
3. Get the project from the playground and run it once locally through the gateway.
4. Choose where the model lives (gateway or native), with the lookup commands for the native model id and where to store the token.
5. Scaffold on the platform (`azd ai agent init`, `agentcore create`, the ADK module, or the Managed Agents definition file).
6. Test locally (`azd ai agent run`, `agentcore dev`, `adk run .`).
7. Deploy and invoke (`azd deploy` and `azd ai agent invoke`, `agentcore deploy` and `agentcore invoke --prompt`, `adk deploy agent_engine` and the query endpoint, `ant apply` and `ant beta:sessions create`).
8. Observe and clean up (`azd down`, `agentcore remove all && agentcore deploy`, delete the reasoning engine, delete the session).

Every command in every guide is parsed with `bash -n` in the test suite, with the `<placeholder>` tokens substituted, so a broken quote cannot ship.

## The deploy script

The short form stays: `GET /v1/blueprints/{id}/deploy/{cloud}` renders one script per cloud with the pricing unit in its header. The Foundry script creates a prompt agent with `PromptAgentDefinition`; the AgentCore script uses the npm AgentCore CLI (`agentcore create`, `agentcore dev`, `agentcore deploy`, `agentcore invoke`), which replaced the Python starter toolkit; the Google script runs `adk deploy agent_engine`; the Anthropic script applies an agent file with `ant apply` and starts a session.

## Running the playground itself

`GET /v1/clouds/self-hosting` and the last section of the page explain how to run the playground on an Azure subscription with `infra/deploy.sh`: sign in with `az login`, clone the private repository with the GitHub CLI, export the secrets, run the script, and register an Entra application to replace development sign-in. There is no public Deploy to Azure button because the repository is private. Sizing and monthly cost are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Sources

- Foundry hosted agents quickstart: https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-hosted-agent
- Foundry DevPack and CLI setup: https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/install-cli-sdk
- AgentCore CLI quickstart and reference: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html
- ADK deployment to Agent Runtime: https://adk.dev/deploy/agent-runtime/deploy/
- Managed Agents quickstart: https://platform.claude.com/docs/en/managed-agents/quickstart
