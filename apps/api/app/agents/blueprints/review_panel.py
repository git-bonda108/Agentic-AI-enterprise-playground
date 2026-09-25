"""Review panel: five critics score a draft, blockers pause for a human verdict, then a revision is written."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config

CRITICS = {
    "legal": "You are corporate counsel. Flag statements that contradict contracts, law or policy.",
    "consistency": "You check internal consistency: numbers, dates and claims that contradict each other.",
    "completeness": "You check whether the draft answers who, what, when and what happens next.",
    "alignment": "You check alignment with company policy: data classification, AI usage and procurement rules.",
    "tone": "You check tone for a professional, respectful audience.",
}
RULES = {
    "legal": ["regardless of contract", "at our discretion", "no limits"],
    "alignment": ["any data", "customer records", "no limits"],
    "tone": ["regardless"],
}


def _heuristic(role: str, text: str) -> dict:
    low = text.lower()
    hits = [p for p in RULES.get(role, []) if p in low]
    if hits:
        return {"score": 2, "issues": [f"Contains '{h}'" for h in hits], "suggestion": "Rewrite to respect contract terms and policy."}
    if role == "completeness" and len(text) < 120:
        return {"score": 3, "issues": ["Very short; missing next steps"], "suggestion": "Add what happens next."}
    return {"score": 4, "issues": [], "suggestion": ""}


def load(state: RunState, config) -> dict:
    inp = state["input"]
    text, title = inp.get("text"), inp.get("title", "Untitled draft")
    if not text and inp.get("draft_id"):
        draft = next((d for d in load_json("drafts.json") if d["id"] == inp["draft_id"]), None)
        if draft:
            text, title = draft["text"], draft["title"]
    text = text or "(empty draft)"
    return {"data": {"title": title, "text": text}, **step(state, "load", f"Loaded draft '{title}' ({len(text)} chars)")}


def critics(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    reviews = {}
    for role, system in CRITICS.items():
        raw = ctx.llm("Economy", system + " Return JSON: {\"score\": 1-5, \"issues\": [..], \"suggestion\": \"..\"}.", f"Title: {d['title']}\nDraft:\n{d['text']}", json_mode=True, max_tokens=400)
        parsed = parse_json(raw, None)
        if not isinstance(parsed, dict) or "score" not in parsed:
            parsed = _heuristic(role, d["text"])
        else:
            # keep deterministic tripwires even when a model is lenient
            rule = _heuristic(role, d["text"])
            if rule["score"] < int(parsed.get("score", 5)):
                parsed = {**parsed, "score": rule["score"], "issues": [*parsed.get("issues", []), *rule["issues"]]}
        reviews[role] = {"score": int(parsed.get("score", 3)), "issues": parsed.get("issues", []), "suggestion": parsed.get("suggestion", "")}
    blockers = [r for r, v in reviews.items() if v["score"] <= 2]
    return {"data": {**d, "reviews": reviews, "blockers": blockers}, **step(state, "critics", f"Five critics reviewed the draft; blockers: {', '.join(blockers) or 'none'}", {"scores": {r: v['score'] for r, v in reviews.items()}}, kind="llm")}


def gate(state: RunState, config) -> dict:
    d = state["data"]
    if not d["blockers"]:
        return {"data": {**d, "verdict": "approved", "notes": ""}, **step(state, "gate", "No blockers; approved automatically", kind="gate")}
    answer = interrupt({
        "question": f"{len(d['blockers'])} critic(s) raised blockers. Approve as is, request a revision, or reject?",
        "options": ["revise", "approve", "reject"],
        "items": [{"label": f"{role} · score {d['reviews'][role]['score']}/5", "detail": "; ".join(d["reviews"][role]["issues"])} for role in d["blockers"]],
        "free_text": "Guidance for the revision",
    })
    decision = answer if isinstance(answer, dict) else {"decision": str(answer), "notes": ""}
    return {"data": {**d, "verdict": decision.get("decision", "revise"), "notes": decision.get("notes", "")}, **step(state, "gate", f"Human verdict: {decision.get('decision')}", decision, kind="human")}


def finalize(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    revised = d["text"]
    if d["verdict"] == "revise":
        issues = "\n".join(f"- {role}: {'; '.join(v['issues'])} ({v['suggestion']})" for role, v in d["reviews"].items() if v["issues"])
        revised = ctx.llm("Workhorse", "You revise business drafts so they satisfy the reviewers' issues while keeping the author's intent. Return the revised draft only, in markdown.", f"Draft:\n{d['text']}\n\nIssues:\n{issues}\n\nHuman guidance: {d['notes']}")
    output = {"verdict": d["verdict"], "critics": d["reviews"], "blockers": d["blockers"], "revised_md": revised, "title": d["title"]}
    return {"output": output, **step(state, "finalize", f"Final verdict: {d['verdict']}", kind="llm" if d["verdict"] == "revise" else "tool")}


def build(checkpointer):
    g = StateGraph(RunState)
    for name, fn in (("load", load), ("critics", critics), ("gate", gate), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "critics")
    g.add_edge("critics", "gate")
    g.add_edge("gate", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="review-panel", name="Review panel", family="Domain", pattern="Five-critic panel with a human verdict",
    summary="Any draft reviewed for legal, consistency, completeness, policy alignment and tone before it ships.",
    description="Five critics score the draft independently. Deterministic tripwires catch known policy violations even if a model is lenient. Any blocker pauses for a human verdict; a revision is written when requested.",
    tiers={"critics": "Economy", "finalize": "Workhorse"},
    graph={"nodes": [{"id": "load", "label": "Load draft", "kind": "tool"}, {"id": "critics", "label": "Five critics", "kind": "llm"}, {"id": "gate", "label": "Human verdict", "kind": "human"}, {"id": "finalize", "label": "Revise or publish", "kind": "llm"}], "edges": [["load", "critics"], ["critics", "gate"], ["gate", "finalize"]], "columns": [["load"], ["critics"], ["gate"], ["finalize"]]},
    samples=[{"name": "Supplier notice with legal issues", "input": {"draft_id": "DRAFT-1"}}, {"name": "AI announcement with policy issues", "input": {"draft_id": "DRAFT-2"}}, {"name": "Clean training update", "input": {"draft_id": "DRAFT-3"}}],
    datasets=["drafts"], flavors=["Microsoft Agent Framework", "CrewAI"],
    review_gates=["Blockers pause for a human verdict"], dashboard=["Drafts reviewed", "Blocker rate", "Revisions requested"],
    links={"origin": "https://github.com/git-bonda108/sage-mind"},
    build=build, input_schema={"draft_id": "sample id", "text": "or free text", "title": "optional"},
))
