"""The per-framework `agent.py` renderers. Every project talks to the playground's OpenAI-compatible gateway.

Each SDK is configured through its OpenAI-compatible client with `PLAYGROUND_BASE_URL`, `PLAYGROUND_TOKEN` and
`PLAYGROUND_MODEL`, so the generated project needs no provider key of its own and every call is governed and metered.
API shapes follow the official quickstarts as of September 2026.
"""

from __future__ import annotations

GATEWAY_PREAMBLE = '''import os

# The playground gateway speaks the OpenAI Chat Completions API. Every call is governed and metered to the token's owner.
BASE_URL = os.environ.get("PLAYGROUND_BASE_URL", "http://localhost:8000/openai/v1")
TOKEN = os.environ.get("PLAYGROUND_TOKEN", "pgk_PASTE_YOUR_PERSONAL_TOKEN")
MODEL = os.environ.get("PLAYGROUND_MODEL", "smart")  # any catalog id, or smart for cost-aware routing
'''


def _helpers():
    from app.flavors import _slug, _tool_stubs, _tools

    return _slug, _tool_stubs, _tools


def render_openai_agents(m: dict) -> dict[str, str]:
    _slug, _tool_stubs, _tools = _helpers()
    tools = ", ".join(_slug(t["id"]) for t in _tools(m))
    agent = f'''"""{m['name']} on the OpenAI Agents SDK, through the playground gateway (or any OpenAI-compatible endpoint)."""
import json
{GATEWAY_PREAMBLE}
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_default_openai_client, set_tracing_disabled
from openai import AsyncOpenAI

client = AsyncOpenAI(base_url=BASE_URL, api_key=TOKEN)
set_default_openai_client(client, use_for_tracing=False)
set_tracing_disabled(True)  # tracing would need an OpenAI platform key; the playground keeps its own traces

{_tool_stubs(m, "@function_tool")}

agent = Agent(
    name="{m['name']}",
    instructions="""{m['description']}""",
    model=OpenAIChatCompletionsModel(model=MODEL, openai_client=client),
    tools=[{tools}],
)

if __name__ == "__main__":
    sample = json.load(open("sample_input.json"))
    result = Runner.run_sync(agent, json.dumps(sample))
    print(result.final_output)
'''
    return {"agent.py": agent}


def render_langgraph(m: dict) -> dict[str, str]:
    _slug, _tool_stubs, _tools = _helpers()
    tools = ", ".join(_slug(t["id"]) for t in _tools(m))
    agent = f'''"""{m['name']} on LangGraph via create_agent, through the playground gateway."""
import json
{GATEWAY_PREAMBLE}
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

{_tool_stubs(m, "")}

model = ChatOpenAI(model=MODEL, base_url=BASE_URL, api_key=TOKEN)
agent = create_agent(model=model, tools=[{tools}], system_prompt="""{m['description']}""")

if __name__ == "__main__":
    sample = json.load(open("sample_input.json"))
    result = agent.invoke({{"messages": [{{"role": "user", "content": json.dumps(sample)}}]}})
    last = result["messages"][-1]
    print(last.content if isinstance(last.content, str) else last.content_blocks)
'''
    return {"agent.py": agent}


def render_crewai(m: dict) -> dict[str, str]:
    _slug, _tool_stubs, _tools = _helpers()
    tools = ", ".join(_slug(t["id"]) for t in _tools(m))
    stubs = "\n".join(f'''@tool("{t['label']}")
def {_slug(t['id'])}(payload: str) -> str:
    """{t['label']}: replace this stub with the deterministic logic from the playground blueprint."""
    return f"{t['label']} done for: {{payload[:60]}}"
''' for t in _tools(m))
    agent = f'''"""{m['name']} as a CrewAI crew, through the playground gateway."""
import json
{GATEWAY_PREAMBLE}
from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

{stubs}

llm = LLM(model=f"openai/{{MODEL}}", base_url=BASE_URL, api_key=TOKEN)
worker = Agent(role="{m['name']}", goal="{m['summary']}", backstory="""{m['description']}""", tools=[{tools}], llm=llm)
task = Task(description="Handle the input: {{payload}}", expected_output="A markdown report", agent=worker)
crew = Crew(agents=[worker], tasks=[task], process=Process.sequential)

if __name__ == "__main__":
    sample = json.load(open("sample_input.json"))
    print(crew.kickoff(inputs={{"payload": json.dumps(sample)}}))
'''
    return {"agent.py": agent}


def render_agent_framework(m: dict) -> dict[str, str]:
    _slug, _tool_stubs, _tools = _helpers()
    tools = ", ".join(_slug(t["id"]) for t in _tools(m))
    agent = f'''"""{m['name']} on Microsoft Agent Framework (Python), through the playground gateway."""
import asyncio
import json
{GATEWAY_PREAMBLE}
from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatClient

{_tool_stubs(m, '@tool(approval_mode="never_require")')}

client = OpenAIChatClient(model_id=MODEL, api_key=TOKEN, base_url=BASE_URL)
agent = Agent(client=client, name="{_slug(m['name'])}", instructions="""{m['description']}""", tools=[{tools}])

if __name__ == "__main__":
    sample = json.load(open("sample_input.json"))
    print(asyncio.run(agent.run(json.dumps(sample))).text)
'''
    return {"agent.py": agent}


def render_adk(m: dict) -> dict[str, str]:
    _slug, _tool_stubs, _tools = _helpers()
    tools = ", ".join(_slug(t["id"]) for t in _tools(m))
    agent = f'''"""{m['name']} on Google ADK through the playground gateway (LiteLLM's OpenAI-compatible route). Run with `adk run .` or `adk web`."""
{GATEWAY_PREAMBLE}
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

{_tool_stubs(m, "")}

root_agent = Agent(
    model=LiteLlm(model=f"openai/{{MODEL}}", api_base=BASE_URL, api_key=TOKEN),
    name="{_slug(m['name'])}",
    description="{m['summary']}",
    instruction="""{m['description']}""",
    tools=[{tools}],
)
'''
    init = "try:\n    from . import agent  # noqa: F401\nexcept ImportError:  # google-adk not installed yet; run pip install -r requirements.txt\n    pass\n"
    return {"agent.py": agent, "__init__.py": init}


RENDERERS = {"openai-agents": render_openai_agents, "langgraph": render_langgraph, "crewai": render_crewai, "agent-framework": render_agent_framework, "adk": render_adk}
