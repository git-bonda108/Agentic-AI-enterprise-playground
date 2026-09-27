"""Cloud platforms: where a blueprint runs outside the playground, how to sign in, and the exact steps to deploy it.

Four runtimes are covered: Microsoft Foundry hosted agents, AWS Bedrock AgentCore Runtime, Google Cloud Agent Runtime
(formerly Vertex AI Agent Engine) and Anthropic Managed Agents. `PLATFORMS` holds each portal, the CLI install and
sign-in commands, the framework fit and the providers whose models are sold natively. `deploy_guide()` turns a blueprint,
a framework, a catalog model and a model mode into an ordered guide whose commands are copyable one by one.

Commands follow the official quickstarts as of September 2026; every step links to the page it came from. The two model
modes are deliberate: `gateway` keeps the deployed agent on the playground's OpenAI-compatible gateway (policies, budgets,
keys and traces still apply; the playground must be reachable from the cloud), `native` points it at the cloud's own model
endpoint so the token spend lands on that cloud bill.
"""

from __future__ import annotations

from app.catalog import get_model
from app.deploy import CLOUDS
from app.flavors import FRAMEWORKS

GATEWAY = "gateway"
NATIVE = "native"
MODES = {
    GATEWAY: "Through the playground gateway: governed, metered and traced; the playground must be reachable from the cloud.",
    NATIVE: "Native provider endpoint: the cloud's own model, billed to the cloud account; the playground is out of the request path.",
}

# Fit of each framework project on each runtime. "first-class" means the runtime's own CLI scaffolds that framework;
# "sample" means an official sample shows the wrapper; "bring your own" means the code deploys as a plain container or
# custom template and you write a small adapter; "harness" means the runtime runs its own loop and the code is not deployed.
FIRST_CLASS, SAMPLE, BYO, HARNESS = "first-class", "sample", "bring your own", "harness"

PLATFORMS: dict[str, dict] = {
    "foundry": {
        "vendor": "Microsoft",
        "portal_url": "https://ai.azure.com",
        "portal_label": "Foundry portal",
        "account_url": "https://portal.azure.com",
        "cli": {
            "name": "Azure Developer CLI (azd) with the Foundry extensions, plus the Azure CLI (az)",
            "install": [
                {"os": "macOS", "cmd": "brew install --cask microsoft/foundry/devpack && foundry-devpack install"},
                {"os": "Windows", "cmd": "winget install Microsoft.FoundryDevPack"},
                {"os": "Linux", "cmd": "curl -fsSL https://aka.ms/foundry-devpack-install.sh | bash"},
                {"os": "Existing azd", "cmd": "azd ext install microsoft.foundry"},
            ],
            "install_docs": "https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/install-cli-sdk",
            "login": ["azd auth login", "az login"],
            "login_note": "Add --tenant-id <tenant> to azd auth login and --tenant <tenant> to az login when your account spans tenants. Both CLIs open a browser; use --use-device-code on a headless machine.",
            "verify": ["azd version", "az account show --output table"],
            "login_docs": "https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli-interactively",
        },
        "roles": "Foundry Project Manager on an existing project, or Owner on the resource group to create a new project.",
        "roles_url": "https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agent-permissions",
        "frameworks": {"agent-framework": FIRST_CLASS, "langgraph": SAMPLE, "openai-agents": SAMPLE, "crewai": BYO, "adk": BYO},
        "frameworks_note": "A hosted agent is any Python or .NET program that serves the Responses protocol on port 8088; azd packages the source, Foundry builds and hosts the container.",
        "samples_url": "https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/hosted-agents",
        "native_providers": ["Azure OpenAI", "OpenAI", "Anthropic", "Mistral", "Cohere", "DeepSeek", "xAI", "Hugging Face", "NVIDIA NIM"],
        "native_note": "Models sold directly by Azure and partner models are deployed into the Foundry project; the deployment name is what the agent calls.",
        "models_url": "https://learn.microsoft.com/en-us/azure/foundry/concepts/foundry-models-overview",
        "model_lookup": ["az cognitiveservices account deployment list --name <foundry-resource> --resource-group <resource-group> --output table"],
        "quickstart_url": "https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-hosted-agent",
        "reference_url": "https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/cli-agent-development",
    },
    "agentcore": {
        "vendor": "Amazon Web Services",
        "portal_url": "https://console.aws.amazon.com/bedrock-agentcore/home",
        "portal_label": "AgentCore console",
        "account_url": "https://console.aws.amazon.com",
        "cli": {
            "name": "AgentCore CLI (npm package @aws/agentcore, Node.js 20 or later) with AWS CLI credentials",
            "install": [
                {"os": "Any", "cmd": "npm install -g @aws/agentcore"},
                {"os": "Verify", "cmd": "agentcore --version"},
            ],
            "install_docs": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html",
            "login": ["aws configure sso", "aws sso login --profile <profile>", "export AWS_PROFILE=<profile> AWS_REGION=us-east-1"],
            "login_note": "IAM Identity Center sign-in is the enterprise path; aws configure with long-lived access keys works but is discouraged. The identity needs the AgentCore API permissions and the CDK bootstrap roles.",
            "verify": ["aws sts get-caller-identity"],
            "login_docs": "https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html",
        },
        "roles": "AgentCore API permissions plus the right to assume the CDK bootstrap roles; bedrock-agentcore:InvokeAgentRuntime to call the deployed agent.",
        "roles_url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html",
        "frameworks": {"langgraph": FIRST_CLASS, "adk": FIRST_CLASS, "openai-agents": FIRST_CLASS, "crewai": BYO, "agent-framework": BYO},
        "frameworks_note": "agentcore create scaffolds Strands, LangChain/LangGraph, Google ADK and OpenAI Agents projects; any other Python loop deploys as a code-based agent with the same entrypoint.",
        "samples_url": "https://github.com/awslabs/amazon-bedrock-agentcore-samples",
        "native_providers": ["Anthropic", "Mistral", "Cohere", "DeepSeek", "OpenAI", "Google"],
        "native_note": "Anthropic, Mistral, Cohere and DeepSeek models are served by Amazon Bedrock; OpenAI, Anthropic and Gemini API keys can also be attached with agentcore add credential.",
        "models_url": "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",
        "model_lookup": [
            "aws bedrock list-foundation-models --by-provider Anthropic --query 'modelSummaries[].modelId' --output table",
            "aws bedrock list-inference-profiles --query 'inferenceProfileSummaries[].inferenceProfileId' --output table",
        ],
        "quickstart_url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html",
        "reference_url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-cli-reference.html",
    },
    "google": {
        "vendor": "Google Cloud",
        "portal_url": "https://console.cloud.google.com/vertex-ai/agents/agent-engines",
        "portal_label": "Agent Runtime console",
        "account_url": "https://console.cloud.google.com",
        "cli": {
            "name": "Google Cloud CLI (gcloud) with the ADK CLI (adk)",
            "install": [
                {"os": "macOS", "cmd": "brew install --cask google-cloud-sdk"},
                {"os": "Any", "cmd": "pip install google-adk"},
            ],
            "install_docs": "https://cloud.google.com/sdk/docs/install",
            "login": [
                "gcloud auth login",
                "gcloud auth application-default login",
                "gcloud config set project <project-id>",
                "gcloud services enable aiplatform.googleapis.com cloudresourcemanager.googleapis.com",
            ],
            "login_note": "The first command signs the CLI in; the second writes Application Default Credentials that the SDK and adk use. Agent Platform API and Cloud Resource Manager API must be enabled on the project.",
            "verify": ["gcloud auth list", "gcloud config get-value project"],
            "login_docs": "https://cloud.google.com/docs/authentication/provide-credentials-adc",
        },
        "roles": "Vertex AI User on the project, plus Service Usage Admin the first time to enable the APIs.",
        "roles_url": "https://adk.dev/deploy/agent-runtime/deploy/",
        "frameworks": {"adk": FIRST_CLASS, "langgraph": SAMPLE, "crewai": BYO, "openai-agents": BYO, "agent-framework": BYO},
        "frameworks_note": "adk deploy agent_engine ships an ADK agent directly; LangGraph has an Agent Runtime template; any other loop deploys as a custom template class with a query method.",
        "samples_url": "https://docs.cloud.google.com/agent-builder/agent-engine/develop/custom",
        "native_providers": ["Google", "Anthropic", "Mistral", "DeepSeek", "Hugging Face"],
        "native_note": "Gemini ids are used as they are; Claude, Mistral, DeepSeek and Hugging Face models are enabled in Model Garden and called through Vertex AI.",
        "models_url": "https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-partner-models",
        "model_lookup": [],
        "quickstart_url": "https://adk.dev/deploy/agent-runtime/deploy/",
        "reference_url": "https://adk.dev/deploy/agent-runtime/test/",
    },
    "anthropic": {
        "vendor": "Anthropic",
        "portal_url": "https://platform.claude.com",
        "portal_label": "Claude Console",
        "account_url": "https://platform.claude.com/settings/keys",
        "cli": {
            "name": "Anthropic CLI (ant) with the anthropic Python SDK",
            "install": [
                {"os": "macOS", "cmd": "brew install anthropics/tap/ant"},
                {"os": "Go", "cmd": "go install github.com/anthropics/anthropic-cli/cmd/ant@latest"},
                {"os": "Any", "cmd": "pip install anthropic"},
            ],
            "install_docs": "https://platform.claude.com/docs/en/managed-agents/quickstart",
            "login": ['export ANTHROPIC_API_KEY="sk-ant-..."'],
            "login_note": "Create the key in the Claude Console under Settings, API keys. Managed Agents is in beta: every request carries the managed-agents-2026-04-01 beta header, which the SDK and CLI add for you.",
            "verify": ["ant --version"],
            "login_docs": "https://platform.claude.com/docs/en/managed-agents/overview",
        },
        "roles": "An organisation API key; Managed Agents is enabled for every API account.",
        "roles_url": "https://platform.claude.com/docs/en/managed-agents/overview",
        "frameworks": {"openai-agents": HARNESS, "langgraph": HARNESS, "crewai": HARNESS, "agent-framework": HARNESS, "adk": HARNESS},
        "frameworks_note": "Managed Agents runs Anthropic's own harness in a sandbox: the blueprint's instructions, tools and MCP servers are deployed, the framework code is not.",
        "samples_url": "https://github.com/anthropics/claude-quickstarts/tree/main/managed-agents",
        "native_providers": ["Anthropic"],
        "native_note": "Claude models only; the catalog id is the Managed Agents model id.",
        "models_url": "https://platform.claude.com/docs/en/managed-agents/agent-setup",
        "model_lookup": [],
        "quickstart_url": "https://platform.claude.com/docs/en/managed-agents/quickstart",
        "reference_url": "https://platform.claude.com/docs/en/managed-agents/reference",
    },
}

SELF_HOSTING = {
    "title": "Run the playground itself on your Azure subscription",
    "intro": "The playground deploys as two Container Apps, PostgreSQL, Key Vault and a dynamic sessions pool from the Bicep template in the repository. The repository is private, so there is no public Deploy to Azure button: clone it with an account that has access and run the script.",
    "steps": [
        {"title": "Sign in to Azure", "body": "Use an account that can create resources in the subscription.", "commands": ["az login", "az account set --subscription <subscription-id>"], "links": [{"label": "Azure portal", "href": "https://portal.azure.com"}]},
        {"title": "Clone the repository", "body": "Access is granted per GitHub account; ask the playground owner if the clone is refused.", "commands": ["gh auth login", "gh repo clone git-bonda108/Agentic-AI-enterprise-playground", "cd Agentic-AI-enterprise-playground"], "links": [{"label": "GitHub CLI", "href": "https://cli.github.com"}]},
        {"title": "Set the secrets", "body": "Platform provider keys are optional; people can bring their own from the Keys drawer once the playground is up.", "commands": [
            "export PG_PASSWORD='a-long-random-password'",
            'export PLAYGROUND_INTERNAL_KEY="$(openssl rand -hex 32)"',
            'export AUTH_SECRET="$(openssl rand -hex 32)"',
            "export PLAYGROUND_KEY_ENCRYPTION_KEY=\"$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')\"",
            "export ANTHROPIC_API_KEY='sk-ant-...'",
        ], "links": []},
        {"title": "Deploy in one command", "body": "The script creates the resource group, builds both images in Azure Container Registry, deploys the template and waits for the health check. Rerunning it rolls a new revision; Container Apps keeps the previous one for rollback.", "commands": ["infra/deploy.sh rg-ai-playground westeurope aiplay"], "links": []},
        {"title": "Switch sign-in to Microsoft Entra ID", "body": "Register an application in the tenant with the redirect URI https://<web-fqdn>/api/auth/callback/microsoft-entra-id and export the three variables before rerunning the script. Development sign-in switches itself off as soon as a client id is present.", "commands": ["export AUTH_MICROSOFT_ENTRA_ID_ID=<client-id> AUTH_MICROSOFT_ENTRA_ID_SECRET=<client-secret> AUTH_MICROSOFT_ENTRA_ID_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0"], "links": []},
    ],
    "cost": "About 90 to 150 USD a month at pilot sizing. Model spend is separate and shown in the cost cockpit.",
    "docs": "https://github.com/git-bonda108/Agentic-AI-enterprise-playground/blob/main/docs/DEPLOYMENT.md",
}


def platforms() -> list[dict]:
    """The four clouds with the runtime rows from `deploy.CLOUDS` merged with the portal, CLI and fit rows."""
    return [{"id": k, **CLOUDS[k], **v} for k, v in PLATFORMS.items()]


def model_fit(cloud: str, model_id: str) -> dict:
    """Whether the catalog model is sold natively on the cloud, and the id the cloud expects."""
    p = PLATFORMS[cloud]
    if model_id == "smart":
        return {"native": False, "provider": "playground", "note": "Smart routing is a playground feature: it only exists through the gateway. Pick a concrete model for native mode."}
    spec = get_model(model_id)
    if spec is None:
        raise KeyError(model_id)
    native = spec.provider in p["native_providers"]
    if cloud == "anthropic":
        note = "The catalog id is the Managed Agents model id." if native else f"Managed Agents runs Claude only; {spec.provider} models cannot be used. The guide substitutes claude-sonnet-5."
    elif cloud == "foundry":
        note = "Deploy the model in the Foundry project (Build, Deployments) and use the deployment name; the resource's OpenAI v1 endpoint speaks the same API as the playground gateway." if native else f"{spec.provider} is not in the Foundry model catalog: keep the gateway mode, or choose a model from a provider Foundry sells."
    elif cloud == "agentcore":
        note = ("Take the Bedrock model id or cross-region inference profile from the lookup commands." if spec.provider in ("Anthropic", "Mistral", "Cohere", "DeepSeek") else "Attach the provider API key with agentcore add credential; the wizard's OpenAI or Gemini provider option uses it.") if native else f"{spec.provider} is not on Amazon Bedrock and has no credential provider in the wizard: keep the gateway mode."
    else:
        note = ("Gemini ids are used as they are with GOOGLE_GENAI_USE_VERTEXAI=1." if spec.provider == "Google" else "Enable the model in Model Garden and use its Vertex id (partner models carry a version suffix such as @20260401).") if native else f"{spec.provider} is not available through Vertex AI: keep the gateway mode."
    return {"native": native, "provider": spec.provider, "note": note}


def _fw_name(framework: str) -> str:
    return FRAMEWORKS[framework]["name"]


def _local_run_step(manifest: dict, framework: str, model_id: str) -> dict:
    fw = FRAMEWORKS[framework]
    folder = f"{manifest['id']}-{framework}"
    return {
        "title": "Get the project from the playground and run it once locally",
        "body": f"Download the {fw['name']} project for {manifest['name']} from the Frameworks page (or the API route below), then run it through the playground gateway with a personal token from Admin, Settings, Personal tokens. A clean local run proves the agent before any cloud resource exists.",
        "commands": [
            f"unzip {folder}.zip && cd {folder}",
            "python -m venv .venv && source .venv/bin/activate",
            fw["install"],
            f'export PLAYGROUND_BASE_URL="https://<your-playground>/openai/v1" PLAYGROUND_TOKEN="pgk_..." PLAYGROUND_MODEL="{model_id}"',
            "python agent.py",
        ],
        "links": [
            {"label": "Frameworks page", "href": f"/discover/frameworks?blueprint={manifest['id']}"},
            {"label": "API route", "href": f"/v1/blueprints/{manifest['id']}/flavor/{framework}/download"},
            {"label": f"{fw['name']} docs", "href": fw["docs"]},
        ],
    }


def _signin_step(cloud: str) -> dict:
    p = PLATFORMS[cloud]
    c = p["cli"]
    return {
        "title": f"Install {c['name'].split(' (')[0]} and sign in",
        "body": f"{c['login_note']} Roles: {p['roles']}",
        "commands": [i["cmd"] for i in c["install"]] + c["login"] + c["verify"],
        "links": [{"label": "Install", "href": c["install_docs"]}, {"label": "Sign in", "href": c["login_docs"]}, {"label": "Permissions", "href": p["roles_url"]}],
    }


def _portal_step(cloud: str) -> dict:
    p = PLATFORMS[cloud]
    what = {
        "foundry": "Create a Foundry project (or open an existing one) and copy the project endpoint from Overview; deploy a chat model under Build, Deployments if you will use native mode.",
        "agentcore": "Open the AgentCore console in the region you will deploy to and confirm Bedrock model access if you will use native mode. First-time accounts should also open the Bedrock model access page.",
        "google": "Select or create the project, enable billing, and open Agent Runtime under Vertex AI, Agents. The console shows every deployed agent, its sessions and its traces.",
        "anthropic": "Create an API key under Settings, API keys. Managed Agents sessions, environments and usage appear in the Console once the first session runs.",
    }[cloud]
    links = [{"label": p["portal_label"], "href": p["portal_url"]}, {"label": "Account", "href": p["account_url"]}]
    if cloud == "agentcore":
        links.append({"label": "Bedrock model access", "href": "https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html"})
    return {"title": f"Sign in to the {p['portal_label']}", "body": what, "commands": [], "links": links}


def _model_step(cloud: str, framework: str, model_id: str, mode: str, fit: dict) -> dict:
    p = PLATFORMS[cloud]
    if mode == GATEWAY:
        body = (
            f"The deployed agent keeps calling the playground gateway with {model_id}, so the role policy, the budget, Smart routing, key resolution and Traces all still apply and the spend stays on the playground ledger. "
            "The playground must be reachable from the cloud (its deployed URL, never localhost) and PLAYGROUND_TOKEN must be stored as a secret of the runtime, not in the source."
        )
        secrets = {
            "foundry": ["# azure.yaml: add PLAYGROUND_BASE_URL and PLAYGROUND_MODEL as env values and PLAYGROUND_TOKEN as a secret reference; azd provision writes them to the hosted agent"],
            "agentcore": ["echo 'PLAYGROUND_TOKEN=pgk_...' >> agentcore/.env.local", "# agentcore.json: add PLAYGROUND_BASE_URL and PLAYGROUND_MODEL to the agent's environment; keep the token out of git"],
            "google": [f"printf 'PLAYGROUND_BASE_URL=https://<your-playground>/openai/v1\\nPLAYGROUND_TOKEN=pgk_...\\nPLAYGROUND_MODEL={model_id}\\n' > .env", "# adk reads .env next to agent.py locally and packages it for Agent Runtime; move the token to Secret Manager for production"],
            "anthropic": ["# no code runs on your side: the MCP Tools entry below carries the playground token in its headers"],
        }[cloud]
        return {"title": "Keep the model on the playground gateway", "body": body, "commands": secrets, "links": [{"label": "Gateway reference", "href": "/discover/frameworks"}, {"label": "Traces", "href": "/operate/traces"}]}
    body = f"{fit['note']} {p['native_note']}"
    commands = list(p["model_lookup"])
    if cloud == "foundry" and fit["native"]:
        commands += [
            "az cognitiveservices account keys list --name <foundry-resource> --resource-group <resource-group> --query key1 --output tsv",
            'export PLAYGROUND_BASE_URL="https://<foundry-resource>.openai.azure.com/openai/v1/" PLAYGROUND_TOKEN="<key1>" PLAYGROUND_MODEL="<deployment-name>"',
            "# agent.py needs no change: the Foundry OpenAI v1 endpoint speaks the same Chat Completions API as the gateway",
        ]
    elif cloud == "agentcore" and fit["native"]:
        commands += (["agentcore add credential"] if fit["provider"] in ("OpenAI", "Google", "Anthropic") else []) + [
            "# keep the Bedrock model client the wizard generated in app/<Agent>/main.py and set its model id from the lookup; move the tools and instructions over from agent.py",
        ]
    elif cloud == "google" and fit["native"]:
        if framework == "adk":
            swap = f'# agent.py: replace LiteLlm(...) with model="{model_id}"' if fit["provider"] == "Google" else '# agent.py: keep LiteLlm and use model="vertex_ai/<vertex-model-id>"'
        else:
            swap = '# agent.py: swap the OpenAI-compatible client for the framework\'s Vertex AI client (ChatVertexAI for LangGraph, LLM(model="vertex_ai/...") for CrewAI)'
        commands += ['export GOOGLE_GENAI_USE_VERTEXAI=1 GOOGLE_CLOUD_PROJECT="<project-id>" GOOGLE_CLOUD_LOCATION="us-central1"', swap]
    elif cloud == "anthropic":
        commands += ["# the model line in the agent definition below is the Managed Agents model id"]
    return {"title": "Point the agent at the cloud's own model", "body": body, "commands": commands, "links": [{"label": "Models", "href": p["models_url"]}]}


def _scaffold_steps(cloud: str, manifest: dict, framework: str, model_id: str, mode: str, fit: dict) -> list[dict]:
    p = PLATFORMS[cloud]
    name = manifest["id"]
    fw_name = _fw_name(framework)
    fit_level = p["frameworks"][framework]
    summary = manifest["summary"].replace('"', "'")[:120]
    if cloud == "foundry":
        wrap = {
            FIRST_CLASS: "The Agent Framework sample is the one azd scaffolds; copy the agent definition from agent.py into its main.py.",
            SAMPLE: f"The samples repository has a {fw_name} hosted agent: initialise from its azure.yaml, then copy the graph and tools from agent.py into its main.py.",
            BYO: f"No official {fw_name} sample exists: start from the Agent Framework sample and replace the agent with the {fw_name} loop from agent.py behind the same Responses server on port 8088.",
        }[fit_level]
        return [
            {"title": "Scaffold the hosted agent", "body": f"{wrap} The wizard asks for the project, tenant, subscription, region and model deployment; azd provision creates the Container Registry, Application Insights and the hosted agent definition.", "commands": [
                'azd ai agent init -m "https://github.com/microsoft-foundry/foundry-samples/blob/main/samples/python/hosted-agents/agent-framework/responses/01-basic/azure.yaml" --deploy-mode code',
                "cd agent-framework-agent-basic-responses",
                f"cp ../{name}-{framework}/agent.py src/",
                "azd provision",
            ], "links": [{"label": "Hosted agent quickstart", "href": p["quickstart_url"]}, {"label": "Samples", "href": p["samples_url"]}]},
            {"title": "Test locally with the agent inspector", "body": "azd creates a virtual environment, installs the dependencies, starts the agent with the startupCommand from azure.yaml and opens the inspector in your browser.", "commands": ["azd ai agent run"], "links": []},
            {"title": "Deploy, invoke and watch the logs", "body": "azd zips the source, Foundry resolves the dependencies and builds the container remotely. The output prints the agent playground link and the agent endpoint.", "commands": [
                "azd deploy",
                f'azd ai agent invoke "{summary}"',
                "azd ai agent monitor --follow",
            ], "links": [{"label": "azd ai reference", "href": p["reference_url"]}]},
            {"title": "Clean up", "body": "azd down deletes the resource group when this environment created the project; with an existing project it leaves the project in place and you delete the hosted agent separately.", "commands": ["azd down"], "links": []},
        ]
    if cloud == "agentcore":
        if mode == NATIVE and fit["provider"] in ("Anthropic", "Mistral", "Cohere", "DeepSeek"):
            provider_flag = "Bedrock"
        elif mode == GATEWAY or fit["provider"] == "OpenAI":
            provider_flag = "OpenAI"
        else:
            provider_flag = "Anthropic" if fit["provider"] == "Anthropic" else "Gemini"
        wizard = {
            FIRST_CLASS: f"Choose Agent, then {fw_name}, then {provider_flag} as the model provider; the wizard writes app/<Agent>/main.py with the framework's client already configured.",
            BYO: f"Choose Agent with the Strands template to get the entrypoint, then replace its loop with the {fw_name} loop from agent.py; the entrypoint handler and the dependencies in pyproject.toml are all AgentCore needs.",
        }[fit_level]
        gateway_note = " In gateway mode the OpenAI provider option is right: set the client's base_url to the playground gateway and its api_key to PLAYGROUND_TOKEN." if mode == GATEWAY else ""
        slug = name.replace("-", "_")
        return [
            {"title": "Create the AgentCore project", "body": f"{wizard}{gateway_note} CodeZip (the default) needs no Docker; Container builds an image.", "commands": [
                "agentcore create",
                f"# non-interactive example: agentcore create --project-name {slug} --name {slug} --language Python --framework Strands --model-provider {provider_flag} --memory none --build CodeZip",
                f"cd {slug}",
                f"cp ../{name}-{framework}/agent.py app/",
            ], "links": [{"label": "AgentCore CLI quickstart", "href": p["quickstart_url"]}, {"label": "Samples", "href": p["samples_url"]}]},
            {"title": "Test locally with the agent inspector", "body": "agentcore dev creates the virtual environment, installs the dependencies, starts a local server with hot reload and opens the inspector to chat with the agent and read its traces.", "commands": ["agentcore dev"], "links": []},
            {"title": "Deploy, invoke and read the logs", "body": "The first deploy bootstraps CDK in the account and takes a few minutes; later deploys are faster. agentcore status prints the runtime ARN for programmatic calls through InvokeAgentRuntime.", "commands": [
                "agentcore deploy --dry-run",
                "agentcore deploy",
                "agentcore status",
                f'agentcore invoke --prompt "{summary}"',
                "agentcore logs --since 30m",
                "agentcore traces list",
            ], "links": [{"label": "CLI reference", "href": p["reference_url"]}]},
            {"title": "Add memory, gateway or identity, then clean up", "body": "Each add command scaffolds configuration in agentcore.json; deploy again to provision it. remove all followed by deploy tears the resources down.", "commands": ["agentcore add memory", "agentcore add gateway", "agentcore remove all && agentcore deploy"], "links": []},
        ]
    if cloud == "google":
        wrap = {
            FIRST_CLASS: "The ADK project deploys as it is: the folder with agent.py and __init__.py is the agent module.",
            SAMPLE: f"Agent Runtime has a {fw_name} template: wrap the graph from agent.py in the template class from the develop guide, then deploy it with the Python SDK.",
            BYO: f"Wrap the {fw_name} loop from agent.py in a custom template class that exposes set_up() and query(), then deploy it with the Python SDK.",
        }[fit_level]
        if fit_level == FIRST_CLASS:
            deploy_cmds = [
                'export PROJECT_ID="<project-id>" LOCATION_ID="us-central1"',
                f'adk deploy agent_engine --project="$PROJECT_ID" --region="$LOCATION_ID" --display_name="{manifest["name"]}" {name}-{framework}',
            ]
        else:
            deploy_cmds = [
                'export PROJECT_ID="<project-id>" LOCATION_ID="us-central1"',
                "pip install google-cloud-aiplatform[agent_engines]",
                "# follow the develop guide: vertexai.agent_engines.create(<your template instance>, requirements=[...], display_name=...)",
            ]
        query_url = '"https://$LOCATION_ID-aiplatform.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION_ID/reasoningEngines/<resource-id>'
        return [
            {"title": "Prepare the agent module", "body": wrap, "commands": [f"cd {name}-{framework}", "adk run ." if fit_level == FIRST_CLASS else "python agent.py"], "links": [{"label": "Standard deployment", "href": p["quickstart_url"]}, {"label": "Custom templates", "href": p["samples_url"]}, {"label": "LangGraph template", "href": "https://docs.cloud.google.com/agent-builder/agent-engine/develop/langgraph"}]},
            {"title": "Deploy to Agent Runtime", "body": "The deploy packages the module, builds it with Cloud Build and creates a reasoning engine resource; the console lists it under Agent Runtime with its resource id.", "commands": deploy_cmds, "links": [{"label": "Agent Runtime overview", "href": "https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview"}]},
            {"title": "Query the deployed agent", "body": "Call the reasoning engine's query method through the REST endpoint or the Python SDK; sessions and traces appear in the console.", "commands": [
                'curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "Content-Type: application/json" ' + query_url + ':query" -d \'{"input": {"message": "Run the sample input"}}\'',
            ], "links": [{"label": "Test the deployment", "href": p["reference_url"]}]},
            {"title": "Clean up", "body": "Delete the reasoning engine when you are done; Agent Runtime bills per vCPU-hour and GiB-hour while it serves.", "commands": ['curl -X DELETE -H "Authorization: Bearer $(gcloud auth print-access-token)" ' + query_url + '"'], "links": [{"label": "Pricing", "href": "https://docs.cloud.google.com/agent-builder/agent-engine/pricing"}]},
        ]
    # anthropic
    model = model_id if fit["native"] else "claude-sonnet-5"
    desc = manifest["description"].replace('"', "'")[:400]
    stream = (
        "python - <<'PY'\nimport json, os\nfrom anthropic import Anthropic\nclient = Anthropic()\nsid = os.environ[\"SESSION_ID\"]\n"
        "with client.beta.sessions.events.stream(sid) as stream:\n"
        "    client.beta.sessions.events.send(sid, events=[{\"type\": \"user.message\", \"content\": [{\"type\": \"text\", \"text\": json.dumps(json.load(open(\"sample_input.json\")))}]}])\n"
        "    for event in stream:\n        if event.type == \"agent.message\":\n            print(\"\".join(b.text for b in event.content if b.type == \"text\"))\n"
        "        elif event.type == \"session.status_idle\":\n            break\nPY"
    )
    return [
        {"title": "Write the agent definition", "body": f"Managed Agents runs its own harness, so the {fw_name} code stays where it is: the blueprint's instructions become the system prompt, the built-in toolset gives bash, files and web, and the playground's MCP server exposes the blueprint's tools and knowledge.", "commands": [
            f"cat > {name}.md <<'MD'\n---\nname: {manifest['name']}\nmodel: {model}\ntools:\n  - type: agent_toolset_20260401\n---\n{desc}\nMD",
            "cat > environment.yaml <<'YAML'\nname: playground-env\nconfig:\n  type: cloud\n  networking:\n    type: unrestricted\nYAML",
        ], "links": [{"label": "Agent setup", "href": p["models_url"]}, {"label": "Tools and MCP", "href": "https://platform.claude.com/docs/en/managed-agents/tools"}]},
        {"title": "Create the agent and the environment", "body": "ant apply prints the ids and records them in claude-lock.json; the same files can be applied again after edits to create a new agent version.", "commands": [f"ant apply {name}.md environment.yaml"], "links": [{"label": "ant apply", "href": "https://platform.claude.com/docs/en/cli-sdks-libraries/cli/apply"}]},
        {"title": "Start a session and send the sample input", "body": "A session is one running instance; send user events and stream the agent's events until session.status_idle.", "commands": [
            'SESSION_ID=$(ant beta:sessions create --agent "$AGENT_ID" --environment-id "$ENVIRONMENT_ID" --title "Playground run" --transform id --raw-output)',
            stream,
        ], "links": [{"label": "Sessions", "href": "https://platform.claude.com/docs/en/managed-agents/sessions"}]},
        {"title": "Clean up", "body": "Sessions persist their transcript and sandbox state server-side; delete the ones you no longer need.", "commands": ['ant beta:sessions delete "$SESSION_ID"'], "links": [{"label": "Reference", "href": p["reference_url"]}]},
    ]


def deploy_guide(manifest: dict, cloud: str, framework: str, model_id: str = "smart", mode: str = GATEWAY) -> dict:
    """An ordered guide for one blueprint on one cloud with one framework and one model choice."""
    if cloud not in PLATFORMS:
        raise KeyError(cloud)
    if framework not in FRAMEWORKS:
        raise KeyError(framework)
    if mode not in MODES:
        raise KeyError(mode)
    fit = model_fit(cloud, model_id)
    if mode == NATIVE and not fit["native"] and cloud != "anthropic":
        mode = GATEWAY
        fit = {**fit, "note": fit["note"] + " The guide below therefore uses the gateway mode."}
    p = PLATFORMS[cloud]
    steps = [_portal_step(cloud), _signin_step(cloud), _local_run_step(manifest, framework, model_id), _model_step(cloud, framework, model_id, mode, fit)]
    steps += _scaffold_steps(cloud, manifest, framework, model_id, mode, fit)
    cost = CLOUDS[cloud]["pricing"].rstrip(".") + "." + (" Token spend stays on the playground ledger in gateway mode." if mode == GATEWAY else " Token spend lands on the cloud bill in native mode.")
    return {
        "cloud": cloud,
        "cloud_name": CLOUDS[cloud]["name"],
        "blueprint_id": manifest["id"],
        "blueprint_name": manifest["name"],
        "framework": framework,
        "framework_name": _fw_name(framework),
        "framework_fit": p["frameworks"][framework],
        "framework_note": p["frameworks_note"],
        "model": model_id,
        "mode": mode,
        "mode_note": MODES[mode],
        "model_fit": fit,
        "cost": cost,
        "steps": [{**s, "number": i + 1} for i, s in enumerate(steps)],
        "filename": f"deploy-{manifest['id']}-{framework}-{cloud}.md",
    }


def guide_markdown(g: dict) -> str:
    lines = [
        f"# {g['blueprint_name']} on {g['cloud_name']} with {g['framework_name']}", "",
        f"Model: {g['model']} ({g['mode']} mode). {g['mode_note']}", "",
        f"Framework fit: {g['framework_fit']}. {g['framework_note']}", "",
        f"Cost: {g['cost']}", "",
    ]
    for s in g["steps"]:
        lines += [f"## {s['number']}. {s['title']}", "", s["body"], ""]
        if s["commands"]:
            lines += ["```bash", *s["commands"], "```", ""]
        if s["links"]:
            lines += ["Links: " + ", ".join(f"[{link['label']}]({link['href']})" for link in s["links"]), ""]
    lines.append("Generated by the Enterprise AI Playground. Commands follow the official quickstarts linked above as of September 2026; check them before running anything that costs money.")
    return "\n".join(lines) + "\n"
