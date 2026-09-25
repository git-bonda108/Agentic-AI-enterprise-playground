"""Cloud flavors: the exact commands to stand a blueprint up on each provider's agent runtime, with the pricing unit shown first."""

from __future__ import annotations

CLOUDS: dict[str, dict] = {
    "foundry": {"name": "Microsoft Foundry", "runtime": "Foundry Agent Service prompt agent", "pricing": "Model tokens at standard rates; hosted agents billed as Container Apps compute", "pricing_url": "https://azure.microsoft.com/en-us/pricing/details/ai-foundry-models/aoai/", "docs": "https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent", "prereq": "az login, a Foundry project endpoint, a deployed model"},
    "anthropic": {"name": "Anthropic Managed Agents", "runtime": "Managed Agents session (beta)", "pricing": "$0.08 per session-hour while running, plus standard token rates", "pricing_url": "https://platform.claude.com/docs/en/about-claude/pricing", "docs": "https://platform.claude.com/docs/en/managed-agents/overview", "prereq": "ANTHROPIC_API_KEY, the ant CLI"},
    "agentcore": {"name": "AWS Bedrock AgentCore", "runtime": "AgentCore Runtime (microVM)", "pricing": "$0.1276 per vCPU-hour and $0.0169 per GB-hour on consumption; idle is free", "pricing_url": "https://aws.amazon.com/bedrock/agentcore/pricing/", "docs": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-toolkit.html", "prereq": "AWS credentials, the agentcore CLI"},
    "google": {"name": "Google Agent Runtime", "runtime": "Agent Runtime on Gemini Enterprise Agent Platform", "pricing": "See the provider pricing page; unit not confirmed at generation time", "pricing_url": "https://cloud.google.com/vertex-ai/pricing", "docs": "https://adk.dev/deploy/", "prereq": "gcloud auth, a project with Vertex AI enabled"},
}


def render_script(manifest: dict, cloud: str) -> dict:
    if cloud not in CLOUDS:
        raise KeyError(cloud)
    name = manifest["id"]
    desc = manifest["description"].replace('"', "'")[:300]
    if cloud == "foundry":
        script = f'''#!/usr/bin/env bash
# Deploy "{manifest['name']}" as a Foundry prompt agent. Prereqs: {CLOUDS[cloud]['prereq']}.
set -euo pipefail
: "${{FOUNDRY_PROJECT_ENDPOINT:?set to https://<resource>.services.ai.azure.com/api/projects/<project>}}"
pip install "azure-ai-projects>=2.3.0" azure-identity
python - <<'PY'
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
agent = project.agents.create_version(
    agent_name="{name}",
    definition=PromptAgentDefinition(model="gpt-5-mini", instructions="""{desc}"""),
)
print("created", agent.id, agent.version)
PY
'''
    elif cloud == "anthropic":
        script = f'''#!/usr/bin/env bash
# Create "{manifest['name']}" as a Managed Agent, then start one session. Prereqs: {CLOUDS[cloud]['prereq']}.
set -euo pipefail
cat > agent.yaml <<'YAML'
name: {name}
model: claude-sonnet-5
system: |
  {desc}
tools:
  - type: agent_toolset_20260401
YAML
ant beta:agents create < agent.yaml
# Then: ant beta:sessions create --agent <agent_id> --message "$(cat sample_input.json)"
'''
    elif cloud == "agentcore":
        script = f'''#!/usr/bin/env bash
# Host "{manifest['name']}" on AgentCore Runtime. Prereqs: {CLOUDS[cloud]['prereq']}.
set -euo pipefail
pip install bedrock-agentcore-starter-toolkit strands-agents
agentcore configure --entrypoint agent.py --name {name.replace('-', '_')}
agentcore launch
agentcore invoke '{{"prompt": "Run the sample input"}}'
'''
    else:
        script = f'''#!/usr/bin/env bash
# Deploy "{manifest['name']}" to Google Agent Runtime with ADK. Prereqs: {CLOUDS[cloud]['prereq']}.
set -euo pipefail
: "${{GOOGLE_CLOUD_PROJECT:?}}" "${{GOOGLE_CLOUD_LOCATION:=us-central1}}"
pip install google-adk
adk deploy agent_engine --project "$GOOGLE_CLOUD_PROJECT" --region "$GOOGLE_CLOUD_LOCATION" --display_name "{manifest['name']}" .
'''
    return {"cloud": cloud, **CLOUDS[cloud], "script": script, "filename": f"deploy-{cloud}-{name}.sh"}
