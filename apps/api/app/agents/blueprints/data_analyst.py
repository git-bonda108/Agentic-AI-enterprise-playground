"""Data analyst: deterministic router to pandas specialists, with the model only narrating the numbers."""

from __future__ import annotations

import pandas as pd
from langgraph.graph import END, START, StateGraph

from app.agents.core import Blueprint, RunState, register, step
from app.agents.data import DATA_DIR, load_csv
from app.agents.runtime import ctx_from_config

DIMENSIONS = {"region": "region", "product": "product", "month": "month", "monthly": "month"}


def load(state: RunState, config) -> dict:
    load_csv("sales.csv")
    df = pd.read_csv(DATA_DIR / "sales.csv")
    df["month"] = df["date"].str.slice(0, 7)
    return {"data": {"rows": len(df), "columns": list(df.columns)}, **step(state, "load", f"Loaded sales.csv: {len(df)} rows, columns {', '.join(df.columns)}")}


def route(state: RunState, config) -> dict:
    q = state["input"].get("question", "").lower()
    kind = "chart" if any(w in q for w in ("chart", "plot", "trend", "graph", "over time")) else "stats" if any(w in q for w in ("total", "sum", "average", "mean", "top", "max", "min", "best", "worst", "most", "least", "highest", "lowest", "count")) else "query"
    dimension = next((v for k, v in DIMENSIONS.items() if k in q), "month" if kind == "chart" else "region")
    metric = "units" if "unit" in q else "revenue"
    return {"data": {**state["data"], "route": kind, "dimension": dimension, "metric": metric}, **step(state, "route", f"Routed to the {kind} specialist: {metric} by {dimension}", kind="gate")}


def compute(state: RunState, config) -> dict:
    d = state["data"]
    df = pd.read_csv(DATA_DIR / "sales.csv")
    df["month"] = df["date"].str.slice(0, 7)
    grouped = df.groupby(d["dimension"])[d["metric"]].sum().reset_index().sort_values(d["dimension"] if d["dimension"] == "month" else d["metric"], ascending=d["dimension"] == "month")
    table = [{d["dimension"]: r[d["dimension"]], d["metric"]: round(float(r[d["metric"]]), 2)} for _, r in grouped.iterrows()]
    chart = {"type": "line" if d["dimension"] == "month" else "bar", "x": d["dimension"], "y": d["metric"], "data": table} if d["route"] == "chart" else None
    total = round(float(df[d["metric"]].sum()), 2)
    return {"data": {**d, "table": table, "chart": chart, "total": total}, **step(state, "compute", f"Computed {d['metric']} by {d['dimension']} with pandas: {len(table)} rows, total {total:,.0f}", {"top": table[:3]})}


def narrate(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    narrative = ctx.llm("Economy", "You explain computed results to a business user in three short sentences. Never invent numbers; use only the table provided.", f"Question: {state['input'].get('question')}\nTable ({d['metric']} by {d['dimension']}): {d['table']}\nTotal: {d['total']}")
    output = {"route": d["route"], "table": d["table"], "chart": d["chart"], "total": d["total"], "narrative_md": narrative, "metric": d["metric"], "dimension": d["dimension"]}
    return {"output": output, **step(state, "narrate", "Narrated the result", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    for name, fn in (("load", load), ("route", route), ("compute", compute), ("narrate", narrate)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "route")
    g.add_edge("route", "compute")
    g.add_edge("compute", "narrate")
    g.add_edge("narrate", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="data-analyst", name="Data analyst", family="Domain", pattern="Deterministic router to specialists",
    summary="Natural-language questions into statistics, queries and charts over a CSV, with every number computed in code.",
    description="A keyword router sends the question to a stats, query or chart specialist. Numbers come from pandas, never from the model; the model only narrates the table it is given.",
    tiers={"route": "deterministic", "compute": "deterministic", "narrate": "Economy"},
    graph={"nodes": [{"id": "load", "label": "Load CSV", "kind": "tool"}, {"id": "route", "label": "Route", "kind": "gate"}, {"id": "compute", "label": "Compute (pandas)", "kind": "tool"}, {"id": "narrate", "label": "Narrate", "kind": "llm"}], "edges": [["load", "route"], ["route", "compute"], ["compute", "narrate"]], "columns": [["load"], ["route"], ["compute"], ["narrate"]]},
    samples=[{"name": "Revenue by region", "input": {"question": "What is the total revenue by region?"}}, {"name": "Monthly trend chart", "input": {"question": "Plot monthly revenue over time"}}, {"name": "Top products by units", "input": {"question": "Which products sold the most units?"}}],
    datasets=["sales"], flavors=["OpenAI Agents SDK", "LangGraph"],
    review_gates=[], dashboard=["Questions answered", "Route mix", "Cost per question"],
    links={"origin": "https://github.com/git-bonda108/multi-agent-data-analysis"},
    build=build, input_schema={"question": "text"},
))
