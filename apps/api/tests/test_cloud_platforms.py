"""Batch 15: cloud platforms with portal links, CLI sign-in, framework fit, model fit and step-by-step deploy guides."""

import re
import subprocess
import tempfile

import pytest

from app.cloud_platforms import (
    BYO,
    FIRST_CLASS,
    HARNESS,
    MODES,
    PLATFORMS,
    SAMPLE,
    SELF_HOSTING,
    model_fit,
)
from app.deploy import CLOUDS
from app.flavors import FRAMEWORKS

PLACEHOLDER = re.compile(r"<[a-z][a-z0-9-]*>")


def _dry_run(commands: list[str]) -> None:
    script = PLACEHOLDER.sub("PLACEHOLDER", "\n".join(commands))
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(script)
    result = subprocess.run(["bash", "-n", f.name], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_every_platform_has_a_portal_a_cli_sign_in_and_a_fit_for_every_framework():
    assert set(PLATFORMS) == set(CLOUDS)
    urls: list[str] = []
    for cloud, p in PLATFORMS.items():
        assert p["portal_url"].startswith("https://") and p["account_url"].startswith("https://")
        cli = p["cli"]
        assert cli["install"] and cli["login"] and cli["verify"], cloud
        assert all(i["os"] and i["cmd"] for i in cli["install"])
        _dry_run([i["cmd"] for i in cli["install"]] + cli["login"] + cli["verify"])
        assert set(p["frameworks"]) == set(FRAMEWORKS), cloud
        assert set(p["frameworks"].values()) <= {FIRST_CLASS, SAMPLE, BYO, HARNESS}
        assert p["native_providers"] and p["quickstart_url"].startswith("https://")
        urls += [p["portal_url"], p["quickstart_url"], p["reference_url"], cli["install_docs"], cli["login_docs"], p["roles_url"], p["models_url"], p["samples_url"]]
    assert all(u.startswith("https://") for u in urls)
    # Sign-in commands are the official ones, not paraphrases.
    assert PLATFORMS["foundry"]["cli"]["login"][:2] == ["azd auth login", "az login"]
    assert "aws sso login --profile <profile>" in PLATFORMS["agentcore"]["cli"]["login"]
    assert PLATFORMS["google"]["cli"]["login"][:2] == ["gcloud auth login", "gcloud auth application-default login"]
    assert PLATFORMS["anthropic"]["cli"]["login"] == ['export ANTHROPIC_API_KEY="sk-ant-..."']
    assert PLATFORMS["anthropic"]["frameworks"]["langgraph"] == HARNESS


def test_clouds_route_returns_platforms_modes_and_frameworks(client, headers):
    body = client.get("/v1/clouds", headers=headers).json()
    assert len(body["clouds"]) == 4
    for c in body["clouds"]:
        assert c["pricing"] and c["portal_url"] and c["cli"]["login"] and c["frameworks"] and c["native_providers"]
    assert set(body["modes"]) == set(MODES)
    assert [f["id"] for f in body["frameworks"]] == list(FRAMEWORKS)


@pytest.mark.parametrize("cloud", list(PLATFORMS))
@pytest.mark.parametrize("framework", list(FRAMEWORKS))
def test_every_cloud_and_framework_yields_an_ordered_guide_whose_commands_parse(client, headers, cloud, framework):
    for model, mode in (("smart", "gateway"), ("claude-sonnet-5", "native"), ("gpt-5.6-terra", "native"), ("groq-gpt-oss-20b", "native")):
        r = client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": cloud, "framework": framework, "model": model, "mode": mode}, headers=headers)
        assert r.status_code == 200, r.text
        g = r.json()
        assert g["cloud"] == cloud and g["framework"] == framework and g["model"] == model
        assert [s["number"] for s in g["steps"]] == list(range(1, len(g["steps"]) + 1)) and len(g["steps"]) >= 8
        assert g["steps"][0]["title"].startswith("Sign in to the") and g["steps"][0]["links"][0]["href"] == PLATFORMS[cloud]["portal_url"]
        assert "sign in" in g["steps"][1]["title"]
        assert any(step["links"] for step in g["steps"]) and all(step["body"] for step in g["steps"])
        _dry_run([c for s in g["steps"] for c in s["commands"]])
        assert g["markdown"].startswith("# Document reconciliation on") and "```bash" in g["markdown"]
        assert g["framework_fit"] == PLATFORMS[cloud]["frameworks"][framework]


def test_native_mode_falls_back_to_the_gateway_when_the_cloud_does_not_sell_the_model(client, headers):
    g = client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "agentcore", "framework": "langgraph", "model": "groq-gpt-oss-20b", "mode": "native"}, headers=headers).json()
    assert g["mode"] == "gateway" and not g["model_fit"]["native"] and "gateway mode" in g["model_fit"]["note"]
    assert any("PLAYGROUND_TOKEN" in c for s in g["steps"] for c in s["commands"])
    native = client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "agentcore", "framework": "langgraph", "model": "claude-sonnet-5", "mode": "native"}, headers=headers).json()
    assert native["mode"] == "native" and native["model_fit"]["native"]
    commands = [c for s in native["steps"] for c in s["commands"]]
    assert any("aws bedrock list-foundation-models" in c for c in commands)
    assert any(c == "agentcore deploy" for c in commands) and any(c.startswith("npm install -g @aws/agentcore") for c in commands)
    assert model_fit("foundry", "smart")["native"] is False
    assert model_fit("anthropic", "gpt-5.6-terra")["native"] is False and "claude-sonnet-5" in model_fit("anthropic", "gpt-5.6-terra")["note"]


def test_guides_carry_the_official_commands_for_each_cloud(client, headers):
    def commands(cloud: str, framework: str, model: str = "smart", mode: str = "gateway") -> str:
        g = client.get("/v1/clouds/guide", params={"blueprint": "knowledge-qa", "cloud": cloud, "framework": framework, "model": model, "mode": mode}, headers=headers).json()
        return "\n".join(c for s in g["steps"] for c in s["commands"])

    foundry = commands("foundry", "agent-framework", "gpt-5.6-terra", "native")
    assert "azd ai agent init" in foundry and "azd provision" in foundry and "azd ai agent run" in foundry and "azd deploy" in foundry and "azd ai agent invoke" in foundry
    assert "openai.azure.com/openai/v1/" in foundry  # native mode reuses the gateway variables against the Foundry OpenAI v1 endpoint
    google = commands("google", "adk", "gemini-2.5-flash", "native")
    assert "gcloud services enable aiplatform.googleapis.com" in google and 'adk deploy agent_engine --project="$PROJECT_ID" --region="$LOCATION_ID"' in google
    assert "GOOGLE_GENAI_USE_VERTEXAI=1" in google and 'model="gemini-2.5-flash"' in google
    anthropic = commands("anthropic", "langgraph", "gpt-5.6-terra", "native")
    assert "ant apply knowledge-qa.md environment.yaml" in anthropic and "model: claude-sonnet-5" in anthropic and "agent_toolset_20260401" in anthropic
    assert "ant beta:sessions create" in anthropic and "session.status_idle" in anthropic
    agentcore = commands("agentcore", "crewai")
    assert "agentcore create" in agentcore and "agentcore dev" in agentcore and "agentcore invoke --prompt" in agentcore and "agentcore remove all && agentcore deploy" in agentcore


def test_guide_download_is_markdown_with_a_filename_and_bad_inputs_are_refused(client, headers):
    r = client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "google", "framework": "adk", "download": 1}, headers=headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown")
    assert r.headers["content-disposition"] == 'attachment; filename="deploy-doc-reconciliation-adk-google.md"'
    assert r.text.startswith("# Document reconciliation on Google Agent Runtime with Google ADK")
    assert client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "nope", "framework": "adk"}, headers=headers).status_code == 404
    assert client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "google", "framework": "nope"}, headers=headers).status_code == 404
    assert client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "google", "framework": "adk", "model": "nope"}, headers=headers).status_code == 404
    assert client.get("/v1/clouds/guide", params={"blueprint": "doc-reconciliation", "cloud": "google", "framework": "adk", "mode": "nope"}, headers=headers).status_code == 422
    assert client.get("/v1/clouds/guide", params={"blueprint": "nope", "cloud": "google", "framework": "adk"}, headers=headers).status_code == 404
    # Catalog entries (non-registry blueprints) get guides too.
    assert client.get("/v1/clouds/guide", params={"blueprint": "lowcode-it-helpdesk", "cloud": "foundry", "framework": "langgraph"}, headers=headers).status_code == 200


def test_self_hosting_guide_explains_the_private_repository_and_parses(client, headers):
    body = client.get("/v1/clouds/self-hosting", headers=headers).json()
    assert body == SELF_HOSTING and "private" in body["intro"]
    assert [s["title"] for s in body["steps"]][:2] == ["Sign in to Azure", "Clone the repository"]
    _dry_run([c for s in body["steps"] for c in s["commands"]])
    assert any("infra/deploy.sh" in c for s in body["steps"] for c in s["commands"])


def test_deploy_scripts_use_the_current_cli_commands(client, headers):
    agentcore = client.get("/v1/blueprints/doc-reconciliation/deploy/agentcore", headers=headers).json()["script"]
    assert "npm install -g @aws/agentcore" in agentcore and "agentcore deploy" in agentcore and "starter-toolkit" not in agentcore
    anthropic = client.get("/v1/blueprints/doc-reconciliation/deploy/anthropic", headers=headers).json()["script"]
    assert "ant apply agent.yaml" in anthropic
