"""Document reconciliation: supervisor-worker with parallel validation and a human gate for escalations."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.core import Blueprint, RunState, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config

SEVERITY = {"over_tolerance": "high", "missing_po": "high", "duplicate_invoice_number": "high", "unknown_vendor": "high", "terms_mismatch": "medium", "date_before_po": "medium"}


def load(state: RunState, config) -> dict:
    invoices = load_json("invoices.json")
    wanted = state["input"].get("invoice_numbers")
    if wanted:
        invoices = [i for i in invoices if i["invoice_number"] in set(wanted)]
    data = {"invoices": invoices, "pos": {p["po_number"]: p for p in load_json("purchase_orders.json")}, "contracts": {c["vendor_id"]: c for c in load_json("contracts.json")}, "tolerance_pct": float(state["input"].get("tolerance_pct", 2.0))}
    return {"data": data, **step(state, "load", f"Loaded {len(invoices)} invoices, {len(data['pos'])} purchase orders, {len(data['contracts'])} contracts")}


def extract(state: RunState, config) -> dict:
    extracted = []
    for inv in state["data"]["invoices"]:
        fields = {k: inv.get(k) for k in ("invoice_number", "vendor_id", "vendor", "po_number", "amount", "currency", "invoice_date", "due_terms")}
        present = sum(1 for v in fields.values() if v not in (None, ""))
        extracted.append({**fields, "confidence": round(present / len(fields), 2), "line_count": len(inv.get("lines", []))})
    return {"data": {**state["data"], "extracted": extracted}, **step(state, "extract", f"Extracted 8 fields from {len(extracted)} invoices with per-field confidence", {"low_confidence": [e["invoice_number"] for e in extracted if e["confidence"] < 1.0]})}


def validate(state: RunState, config) -> dict:
    d = state["data"]
    tol = d["tolerance_pct"]
    seen: dict[str, int] = {}
    anomalies = []
    for e in d["extracted"]:
        seen[e["invoice_number"]] = seen.get(e["invoice_number"], 0) + 1
    for e in d["extracted"]:
        po = d["pos"].get(e["po_number"]) if e["po_number"] else None
        contract = d["contracts"].get(e["vendor_id"])
        found = []
        if not e["po_number"]:
            found.append("missing_po")
        elif po:
            if e["amount"] > po["amount"] * (1 + tol / 100) + 0.01:
                found.append("over_tolerance")
            if e["invoice_date"] < po["issued"]:
                found.append("date_before_po")
        if seen[e["invoice_number"]] > 1:
            found.append("duplicate_invoice_number")
        if contract is None:
            found.append("unknown_vendor")
        elif e["due_terms"] != contract["payment_terms"]:
            found.append("terms_mismatch")
        for code in found:
            anomalies.append({"invoice_number": e["invoice_number"], "code": code, "severity": SEVERITY[code], "po_number": e["po_number"], "amount": e["amount"]})
    return {"data": {**d, "anomalies": anomalies}, **step(state, "validate", f"Cross-checked against purchase orders, contracts and master data: {len(anomalies)} anomalies", {"codes": sorted({a['code'] for a in anomalies})})}


def quality(state: RunState, config) -> dict:
    d = state["data"]
    by_inv: dict[str, list] = {}
    for a in d["anomalies"]:
        by_inv.setdefault(a["invoice_number"], []).append(a)
    results = []
    for e in d["extracted"]:
        issues = by_inv.get(e["invoice_number"], [])
        risk = "high" if any(i["severity"] == "high" for i in issues) else "medium" if issues else "low"
        results.append({"invoice_number": e["invoice_number"], "vendor": e["vendor"], "amount": e["amount"], "risk": risk, "anomalies": [i["code"] for i in issues], "decision": "escalate" if risk != "low" else "approve"})
    escalated = [r for r in results if r["decision"] == "escalate"]
    return {"data": {**d, "results": results, "escalated": escalated}, **step(state, "quality", f"{len(results) - len(escalated)} auto-approved, {len(escalated)} escalated for review", kind="gate")}


def decide(state: RunState, config) -> dict:
    escalated = state["data"]["escalated"]
    if not escalated or state["input"].get("auto_approve"):
        return {"data": {**state["data"], "decision": {"decision": "auto", "notes": ""}}, **step(state, "decide", "No human decision needed", kind="human")}
    answer = interrupt({
        "question": f"{len(escalated)} invoices need a decision. Approve them, reject them, or approve with notes?",
        "options": ["approve", "approve_with_notes", "reject"],
        "items": [{"label": f"{r['invoice_number']} · {r['vendor']} · ${r['amount']:,.2f}", "detail": ", ".join(r["anomalies"])} for r in escalated],
        "free_text": "Notes for the audit trail",
    })
    decision = answer if isinstance(answer, dict) else {"decision": str(answer), "notes": ""}
    return {"data": {**state["data"], "decision": decision}, **step(state, "decide", f"Human decision: {decision.get('decision')}", decision, kind="human")}


def report(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    table = "\n".join(f"- {r['invoice_number']} ({r['vendor']}, ${r['amount']:,.2f}): {', '.join(r['anomalies']) or 'clean'} -> {r['decision']}" for r in d["results"])
    narrative = ctx.llm("Workhorse", "You write concise accounts-payable reconciliation summaries for a finance controller. Use markdown with a short headline, three bullets on the main findings, and one line on the decision taken.", f"Tolerance: {d['tolerance_pct']}%.\nDecision: {d['decision']}.\nResults:\n{table}")
    output = {"summary_md": narrative, "invoices": d["results"], "anomalies": d["anomalies"], "escalated": [r["invoice_number"] for r in d["escalated"]], "decision": d["decision"], "counts": {"invoices": len(d["results"]), "anomalies": len(d["anomalies"]), "escalated": len(d["escalated"])}}
    return {"output": output, **step(state, "report", "Wrote the controller summary", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    for name, fn in (("load", load), ("extract", extract), ("validate", validate), ("quality", quality), ("decide", decide), ("report", report)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "extract")
    g.add_edge("extract", "validate")
    g.add_edge("validate", "quality")
    g.add_edge("quality", "decide")
    g.add_edge("decide", "report")
    g.add_edge("report", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="doc-reconciliation", name="Document reconciliation", family="Domain", pattern="Supervisor-worker, parallel validation, human gate",
    summary="Extract, cross-check and escalate invoices against purchase orders, contracts and vendor master data.",
    description="A manager stage extracts fields with per-field confidence, validates every invoice against its purchase order, the vendor contract and master data, scores risk, escalates anything risky to a human decision, and writes a controller-ready summary. The core is deterministic; only the narrative is generated.",
    tiers={"extraction": "deterministic", "validation": "deterministic", "report": "Workhorse"},
    graph={"nodes": [{"id": "load", "label": "Load documents", "kind": "tool"}, {"id": "extract", "label": "Extract fields", "kind": "tool"}, {"id": "validate", "label": "Validate", "kind": "tool"}, {"id": "quality", "label": "Quality gate", "kind": "gate"}, {"id": "decide", "label": "Human decision", "kind": "human"}, {"id": "report", "label": "Write summary", "kind": "llm"}], "edges": [["load", "extract"], ["extract", "validate"], ["validate", "quality"], ["quality", "decide"], ["decide", "report"]], "columns": [["load"], ["extract"], ["validate"], ["quality"], ["decide"], ["report"]]},
    samples=[{"name": "All 20 invoices, 2% tolerance", "input": {"tolerance_pct": 2}}, {"name": "Three suspicious invoices", "input": {"invoice_numbers": ["INV-9002", "INV-9005", "INV-9012"]}}, {"name": "Auto-approve for a batch report", "input": {"tolerance_pct": 5, "auto_approve": True}}],
    datasets=["invoices", "purchase_orders", "contracts"], flavors=["LangGraph", "OpenAI Agents SDK", "CrewAI"],
    review_gates=["Escalated invoices pause for a human decision"], dashboard=["Invoices processed", "Anomaly rate", "Escalation rate", "Cost per invoice"],
    links={"pattern": "https://docs.langchain.com/oss/python/langgraph/interrupts", "origin": "https://github.com/git-bonda108/agentic-invoice-processing"},
    build=build,
    input_schema={"tolerance_pct": "number, percent", "invoice_numbers": "optional list of invoice ids", "auto_approve": "optional boolean"},
))
