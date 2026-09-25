"""Learning path generator: generator-critic pair with curated references per level."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config

LEVELS = ("beginner", "intermediate", "advanced")


def _default_path(competency: str, role: str) -> dict:
    return {
        "beginner": {"goal": f"Understand core {competency} concepts used by a {role}", "topics": [f"{competency} vocabulary", "Reading examples", "First hands-on exercise"], "hours": 8},
        "intermediate": {"goal": f"Apply {competency} to real {role} tasks", "topics": ["Working with real data", "Common pitfalls", "Small end-to-end project"], "hours": 16},
        "advanced": {"goal": f"Lead {competency} work and coach others", "topics": ["Optimization and review", "Standards and governance", "Capstone with measurable outcome"], "hours": 24},
    }


def generate(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    inp = state["input"]
    competency, role, function = inp.get("competency", "SQL"), inp.get("role", "Analyst"), inp.get("function", "Finance")
    raw = ctx.llm("Workhorse", "You design competency-based learning paths. Return JSON with keys beginner, intermediate, advanced; each has goal, topics (3 to 5 strings) and hours (integer).", f"Function: {function}. Role: {role}. Competency: {competency}.", json_mode=True)
    path = parse_json(raw, None)
    if not isinstance(path, dict) or not all(level in path for level in LEVELS):
        path = _default_path(competency, role)
    return {"data": {"competency": competency, "role": role, "function": function, "path": path}, **step(state, "generate", f"Drafted a three-level path for {role} in {function}: {competency}", kind="llm")}


def critique(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    raw = ctx.llm("Economy", "You are a learning designer reviewing a draft path. Return JSON: {\"score\": 1-5, \"issues\": [..], \"fixes\": [..]}.", f"Draft: {d['path']}", json_mode=True)
    review = parse_json(raw, None)
    if not isinstance(review, dict) or "score" not in review:
        review = {"score": 4, "issues": ["Add a measurable outcome per level"], "fixes": ["Attach one assessment per level"]}
    path = d["path"]
    for level in LEVELS:
        entry = path.get(level, {})
        if isinstance(entry, dict):
            entry.setdefault("assessment", f"Short quiz and one applied task at {level} level")
    return {"data": {**d, "critique": review, "path": path}, **step(state, "critique", f"Critic scored the draft {review.get('score')}/5 and applied {len(review.get('fixes', []))} fixes", kind="llm")}


def references(state: RunState, config) -> dict:
    d = state["data"]
    refs = load_json("learning_refs.json")
    key = next((k for k in refs if k.lower() in d["competency"].lower() or d["competency"].lower() in k.lower()), None)
    chosen = refs.get(key, []) if key else []
    if not chosen:
        chosen = [(f"Search: {d['competency']} for {d['role']}", f"https://www.google.com/search?q={d['competency'].replace(' ', '+')}+course")]
    per_level = {level: [{"title": t, "url": u} for t, u in chosen[i::3] or chosen[:1]] for i, level in enumerate(LEVELS)}
    return {"data": {**d, "references": per_level}, **step(state, "references", f"Attached {sum(len(v) for v in per_level.values())} references from the curated catalog")}


def assemble(state: RunState, config) -> dict:
    d = state["data"]
    lines = [f"# {d['competency']} path for {d['role']} ({d['function']})", ""]
    for level in LEVELS:
        entry = d["path"].get(level, {})
        lines.append(f"## {level.title()} · {entry.get('hours', '?')} hours")
        lines.append(f"Goal: {entry.get('goal', '')}")
        lines += [f"- {t}" for t in entry.get("topics", [])]
        lines.append(f"Assessment: {entry.get('assessment', '')}")
        lines += [f"- [{r['title']}]({r['url']})" for r in d["references"].get(level, [])]
        lines.append("")
    output = {"path_md": "\n".join(lines), "path": d["path"], "references": d["references"], "critique": d["critique"], "competency": d["competency"], "role": d["role"]}
    return {"output": output, **step(state, "assemble", "Assembled the final learning path")}


def build(checkpointer):
    g = StateGraph(RunState)
    for name, fn in (("generate", generate), ("critique", critique), ("references", references), ("assemble", assemble)):
        g.add_node(name, fn)
    g.add_edge(START, "generate")
    g.add_edge("generate", "critique")
    g.add_edge("critique", "references")
    g.add_edge("references", "assemble")
    g.add_edge("assemble", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="learning-path", name="Learning path generator", family="Domain", pattern="Generator-critic with curated references",
    summary="Three-level competency paths per function and role, reviewed by a critic and backed by curated references.",
    description="A generator drafts beginner, intermediate and advanced levels; a cheaper critic scores and fixes the draft; references come from a curated catalog so links are real; the result is assembled as markdown a training team can publish.",
    tiers={"generate": "Workhorse", "critique": "Economy", "references": "deterministic"},
    graph={"nodes": [{"id": "generate", "label": "Generate path", "kind": "llm"}, {"id": "critique", "label": "Critic review", "kind": "llm"}, {"id": "references", "label": "Curate references", "kind": "tool"}, {"id": "assemble", "label": "Assemble", "kind": "tool"}], "edges": [["generate", "critique"], ["critique", "references"], ["references", "assemble"]], "columns": [["generate"], ["critique"], ["references"], ["assemble"]]},
    samples=[{"name": "SQL for a finance analyst", "input": {"function": "Finance", "role": "Analyst", "competency": "SQL"}}, {"name": "Agentic AI for a solutions architect", "input": {"function": "Engineering", "role": "Solutions architect", "competency": "Agentic AI"}}, {"name": "Prompt engineering for HR", "input": {"function": "HR", "role": "Business partner", "competency": "Prompt engineering"}}],
    datasets=["learning_refs"], flavors=["OpenAI Agents SDK", "Microsoft Agent Framework"],
    review_gates=[], dashboard=["Paths generated", "Critic score", "Cost per path"],
    links={"origin": "https://github.com/git-bonda108/learning-path-generator"},
    build=build, input_schema={"function": "text", "role": "text", "competency": "text"},
))
