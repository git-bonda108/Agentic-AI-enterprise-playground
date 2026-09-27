"""Seed a demo tenant: ten people across departments, a month of governed usage, runs, knowledge, agents, evaluations, a canary,
showcase posts and a judged challenge. Everything is generated offline (the fake provider), so it costs nothing and is repeatable.

Run: `uv run python scripts/seed_demo.py [--reset]` from apps/api, or `npm run seed:demo` from the repository root.
The script talks to the database the API uses (PLAYGROUND_DATABASE_URL); the API may keep running while it seeds.
"""

from __future__ import annotations

import os
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

os.environ["PLAYGROUND_FAKE_LLM"] = "true"  # never spend money seeding
os.environ.setdefault("PLAYGROUND_CANARY_SCHEDULER", "false")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.agents import registry as _registry  # noqa: F401
from app.agents.runtime import resume_run, start_run
from app.catalog import estimate_cost, get_model
from app.community import (
    achievements_for,
    close_challenge,
    judge_submission,
    toggle_like,
)
from app.db import SessionLocal, init_db
from app.evals import ensure_system_suites, execute_eval, next_due, run_canary
from app.governance import seed_defaults
from app.knowledge import dataset_units, ingest_text
from app.models import (
    Achievement,
    CanarySchedule,
    Challenge,
    ChallengeSubmission,
    Conversation,
    CustomAgent,
    EvalRun,
    EvalSuite,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSpace,
    Message,
    Promotion,
    Run,
    ShowcaseComment,
    ShowcaseItem,
    ShowcaseLike,
    UsageEvent,
    User,
)

SEED_TAG = "demo-seed"
random.seed(20260926)

PEOPLE = [
    ("u1", "Satya Bonda", "satya@playground.local", "admin", "AI Platform"),
    ("u2", "Priya Raman", "priya@playground.local", "champion", "R&A Training"),
    ("u3", "Daniel Okafor", "daniel@playground.local", "builder", "Finance"),
    ("u4", "Mei Lin", "mei@playground.local", "builder", "Engineering"),
    ("u5", "Carlos Mendes", "carlos@playground.local", "explorer", "Sales"),
    ("u6", "Aisha Khan", "aisha@playground.local", "explorer", "HR"),
    ("u7", "Tom Becker", "tom@playground.local", "builder", "Operations"),
    ("u8", "Hannah Weiss", "hannah@playground.local", "explorer", "Legal"),
    ("u9", "Ravi Iyer", "ravi@playground.local", "champion", "Procurement"),
    ("u10", "Elena Rossi", "elena@playground.local", "explorer", "Marketing"),
    ("u11", "Arbaz Sayed", "arbazsayed105@gmail.com", "builder", "Partners"),  # real pilot participants: seeded as people, never with fabricated activity
    ("u12", "Toral Rathod", "Toral.Rathod@eduramp.in", "builder", "Eduramp"),
    ("u13", "Joy Das", "Joy.Das@wns.com", "builder", "WNS"),
    ("u14", "Amal Socratles", "Amal.Socraties@wns.com", "builder", "WNS"),
]
ACTIVITY = {"u1": 6, "u2": 5, "u3": 4, "u4": 5, "u5": 2, "u6": 2, "u7": 3, "u8": 1, "u9": 3, "u10": 2, "u11": 0, "u12": 0, "u13": 0, "u14": 0}  # sessions per week; real people get none
MODEL_MIX = ["claude-sonnet-5", "claude-sonnet-5", "claude-haiku-4-5", "claude-haiku-4-5", "claude-haiku-4-5", "gpt-5.6-terra", "deepseek-v4-flash", "claude-opus-5-5"]
PROMPTS = [
    "Summarise the travel policy for a new joiner", "Draft a polite reminder to a supplier about an overdue invoice", "Explain the difference between a purchase order and a goods receipt",
    "Rewrite this paragraph for executives", "Give me five interview questions for a data analyst", "What are the risks in this contract clause?",
    "Turn these bullet points into a status update", "Compare two vendor proposals on cost and delivery", "Write SQL to find duplicate invoices", "Outline a 30-minute AI literacy session",
]


def log(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr)


def seed_users(db) -> dict[str, User]:
    users = {}
    for uid, name, email, role, dept in PEOPLE:
        u = db.get(User, uid)
        if u is None:
            u = User(id=uid, email=email, name=name, role=role, department=dept)
            db.add(u)
        users[uid] = u
    db.commit()
    return users


def seed_usage(db, users: dict[str, User], days: int = 30) -> int:
    now = datetime.now(UTC)
    events = 0
    for uid in users:
        for _ in range(ACTIVITY[uid] * days // 7):
            start = (now - timedelta(days=random.uniform(0.2, days))).replace(hour=random.choice([9, 10, 11, 14, 15, 16]), minute=random.randint(0, 59))
            model_id = random.choice(MODEL_MIX)
            spec = get_model(model_id)
            conv = Conversation(user_id=uid, title=random.choice(PROMPTS), model=model_id, created_at=start, updated_at=start)
            db.add(conv)
            db.flush()
            t = start
            for _turn in range(random.randint(1, 4)):
                tokens_in, tokens_out = random.randint(300, 2500), random.randint(120, 900)
                cost = estimate_cost(model_id, tokens_in, tokens_out)
                routed = random.random() < 0.35
                db.add(Message(conversation_id=conv.id, role="user", content=random.choice(PROMPTS), created_at=t))
                db.add(Message(conversation_id=conv.id, role="assistant", content="(seeded reply)", model=model_id, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, latency_ms=random.randint(900, 4200), created_at=t + timedelta(seconds=8)))
                db.add(UsageEvent(user_id=uid, conversation_id=conv.id, feature="compare" if random.random() < 0.15 else "chat", model=model_id, provider=spec.provider if spec else "unknown", tokens_in=tokens_in, tokens_out=tokens_out, tokens_cached=int(tokens_in * random.choice([0, 0, 0.4])), cost_usd=cost, latency_ms=random.randint(900, 4200), status="ok", routed=routed, routed_tier=spec.tier if (routed and spec) else None, savings_usd=round(cost * 2.2, 6) if routed else 0.0, created_at=t + timedelta(seconds=9)))
                events += 1
                t += timedelta(minutes=random.randint(2, 9))
    db.commit()
    return events


def run_blueprint(blueprint_id: str, payload: dict, uid: str, resume=None, backdate_days: float = 0.0) -> Run:
    with SessionLocal() as db:
        run = Run(blueprint_id=blueprint_id, user_id=uid, input=payload, status="queued", source="demo")
        db.add(run)
        db.commit()
        start_run(run, background=False)
        db.expire(run)
        run = db.get(Run, run.id)
        hops = 0
        while run.status == "waiting_review" and hops < 3:
            answer = resume if resume is not None else ((run.review or {}).get("options") or ["approve"])[0]
            resume_run(run, answer, background=False)
            db.expire(run)
            run = db.get(Run, run.id)
            hops += 1
        if backdate_days:
            shift = timedelta(days=backdate_days)
            run.created_at, run.updated_at = run.created_at - shift, run.updated_at - shift
            if run.finished_at:
                run.finished_at -= shift
            for e in db.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id)).all():
                e.created_at -= shift
            db.commit()
        return run


def seed_runs() -> list[Run]:
    plan = [
        ("doc-reconciliation", {"tolerance_pct": 2}, "u3", {"decision": "approve", "notes": "Escalations reviewed by finance"}),
        ("doc-reconciliation", {"invoice_numbers": ["INV-9002"], "tolerance_pct": 15}, "u3", None),
        ("sage-lens", {"question": "How does Microsoft sell AI models to enterprises?"}, "u2", None),
        ("sage-lens", {"question": "Where are Anthropic's Claude models available?"}, "u4", None),
        ("learning-path", {"function": "Finance", "role": "Analyst", "competency": "SQL"}, "u2", None),
        ("learning-path", {"function": "Engineering", "role": "Solutions architect", "competency": "Agentic AI"}, "u4", None),
        ("review-panel", {"draft_id": "DRAFT-2"}, "u8", "reject"),
        ("data-analyst", {"question": "What is the total revenue by region?"}, "u7", None),
        ("knowledge-qa", {"question": "What is the hotel limit per night when travelling?"}, "u6", None),
        ("knowledge-qa", {"question": "What do I need for a purchase over 50,000 USD?"}, "u9", None),
        ("knowledge-qa", {"question": "Can I paste payroll data into an external AI tool?"}, "u5", None),
        ("adoption-digest", {"days": 30, "audience": "executives"}, "u1", None),
    ]
    runs = []
    for bp, payload, uid, resume in plan:
        runs.append(run_blueprint(bp, payload, uid, resume, backdate_days=random.uniform(0.5, 25)))
        log(f"run {bp} for {uid}: {runs[-1].status}")
    return runs


def seed_knowledge_and_agents(db, users: dict[str, User]) -> tuple[KnowledgeSpace, list[CustomAgent]]:
    space = KnowledgeSpace(owner_id="u2", name="Finance and travel policies", description="Policies every new joiner asks about", visibility="org", department="R&A Training", embedding_model="local-hash")
    db.add(space)
    db.commit()
    ingest_text(db, space, users["u2"], "Travel policy", "Hotel stays are reimbursed up to 220 USD per night in major cities and 150 USD elsewhere.\n\nTaxi rides are reimbursed with a receipt. Ride sharing is allowed for business travel.\n\nBusiness class flights require director approval when the flight is longer than 8 hours.\n\nClaims must be filed within 30 days of travel.", "text")
    ingest_text(db, space, users["u2"], "Expense rules", "Meals are reimbursed up to 60 USD per day with receipts. Alcohol is never reimbursed. Client entertainment needs a manager's pre-approval above 200 USD.", "text")
    title, chunks, metas = dataset_units("policies")
    ingest_text(db, space, users["u2"], title, "\n\n".join(chunks), "dataset", "policies", metas=metas, chunks=chunks)
    agents = [
        CustomAgent(id="custom-demo-travel", user_id="u2", name="Travel desk", description="Answers travel and expense questions with the policy cited.", instructions="You answer travel and expense questions using the policies provided and always cite the policy id in brackets. If a rule is not in the policies, say so.", knowledge=["policies", f"space:{space.id}"], tools=[], skills=[], starters=["What is the hotel limit per night?", "Can I claim taxi rides?", "How do I file a claim?"], published=True),
        CustomAgent(id="custom-demo-vendor", user_id="u9", name="Vendor onboarding guide", description="Walks a buyer through onboarding a new vendor.", instructions="You guide procurement colleagues through vendor onboarding using the policies provided. List the documents needed, who approves, and cite the policy id.", knowledge=["policies"], tools=["playground/mcp"], skills=[], starters=["What do I need to onboard a vendor?", "Who approves master data changes?"], published=True),
    ]
    for a in agents:
        if db.get(CustomAgent, a.id) is None:
            db.add(a)
    db.commit()
    return space, agents


def seed_evals(db, agents: list[CustomAgent]) -> None:
    ensure_system_suites(db)
    kqa = db.scalar(select(EvalSuite).where(EvalSuite.blueprint_id == "knowledge-qa", EvalSuite.system.is_(True)))
    travel = EvalSuite(owner_id="u2", blueprint_id=agents[0].id, name="Travel desk regression set", description="Questions new joiners actually ask",
                       cases=[{"id": f"c{i + 1}", "name": q[:60], "input": {"task": q}, "expect": {"status": "completed", "contains": "POL-001"}} for i, q in enumerate(["What is the hotel limit per night?", "How much can I claim for meals?", "Do I need approval for business class?", "When must I file my claim?", "Are taxi rides reimbursed?"])],
                       rubric={"criteria": [{"id": "correctness", "weight": 1}, {"id": "groundedness", "weight": 1}], "pass_threshold": 3.0}, gate={"min_pass_rate": 90, "max_cost_per_case_usd": 0.5, "max_p95_ms": 60000})
    db.add(travel)
    db.commit()
    for suite, uid in ((kqa, "u1"), (travel, "u2")):
        for _ in range(2):
            er = EvalRun(suite_id=suite.id, blueprint_id=suite.blueprint_id, user_id=uid, kind="manual", status="queued")
            db.add(er)
            db.commit()
            execute_eval(er.id)
        sched = CanarySchedule(suite_id=suite.id, enabled=True, hour_utc=2, auto_rollback=True, next_due_at=next_due(2))
        db.add(sched)
        db.commit()
        for _ in range(3):
            run_canary(sched.id, wait=True)
        log(f"evaluated and canaried '{suite.name}'")


def seed_community(db, users: dict[str, User], runs: list[Run], agents: list[CustomAgent]) -> None:
    posts = [
        ("u3", "run", next(r for r in runs if r.blueprint_id == "doc-reconciliation").id, "Twenty-four invoices reconciled before the morning stand-up", "The document reconciliation agent matched invoices to purchase orders, contracts and master data, flagged six for review and drafted the controller's summary. I approved the escalations in the run page.", "Two hours of matching removed from the month-end close", ["finance", "reconciliation"]),
        ("u2", "agent", agents[0].id, "A travel desk that cites the policy every time", "Built in the wizard in ten minutes: instructions, the policy Knowledge Space and three starter prompts. New joiners get the hotel limit with the policy id attached.", "Zero policy questions in the onboarding channel this week", ["hr", "policies", "wizard"]),
        ("u4", "run", next(r for r in runs if r.blueprint_id == "sage-lens").id, "Deep research on model availability, with sources", "Sage Lens asked one clarifying question, searched in parallel and wrote a brief with three cited sources. Good enough to paste into the architecture review.", "Half a day of research done in four minutes", ["research", "models"]),
        ("u9", "agent", agents[1].id, "Vendor onboarding, explained by an agent", "Procurement's onboarding checklist as a wizard agent that can also call the playground's own tools through the MCP connector.", "Onboarding questions answered on first contact", ["procurement", "connectors"]),
    ]
    items = []
    for uid, kind, ref, title, summary, outcome, tags in posts:
        item = ShowcaseItem(owner_id=uid, kind=kind, ref_id=ref, title=title, summary=summary, outcome=outcome, tags=[*tags, SEED_TAG], likes=0, views=random.randint(4, 40), created_at=datetime.now(UTC) - timedelta(days=random.uniform(1, 12)))
        db.add(item)
        items.append(item)
    db.commit()
    for item in items:
        for uid in random.sample(list(users), random.randint(2, 6)):
            if uid != item.owner_id:
                toggle_like(db, item, users[uid])
    challenge = Challenge(owner_id="u2", title="Policy answers sprint", brief="Build an agent that answers policy questions with a citation. Judged on correctness and groundedness against the same two questions for everyone.", cases=[{"input": {"question": "What is the hotel limit per night?"}, "expect": {"status": "completed", "contains": "POL-001"}}, {"input": {"question": "What do I need for a purchase over 50,000 USD?"}, "expect": {"contains": "POL-002"}}], rubric={"criteria": [{"id": "correctness", "weight": 1}, {"id": "groundedness", "weight": 1}], "pass_threshold": 3.0}, badge="Policy pro", ends_at=datetime.now(UTC) + timedelta(days=5))
    db.add(challenge)
    db.commit()
    for uid, agent_id, note in (("u1", "knowledge-qa", "The built-in one"), ("u2", agents[0].id, "Wizard agent with the policy space")):
        sub = ChallengeSubmission(challenge_id=challenge.id, user_id=uid, agent_id=agent_id, note=note)
        db.add(sub)
        db.commit()
        judge_submission(db, challenge, sub)
    close_challenge(db, challenge)
    for u in users.values():
        achievements_for(db, u)
    log("showcase, challenge and achievements seeded")


def reset(db) -> None:
    for model in (ShowcaseLike, ShowcaseComment, ShowcaseItem, ChallengeSubmission, Challenge, Achievement, Promotion, CanarySchedule, EvalRun, KnowledgeChunk, KnowledgeDocument, KnowledgeSpace, UsageEvent, Message, Conversation, Run):
        for row in db.scalars(select(model)).all():
            db.delete(row)
    for s in db.scalars(select(EvalSuite).where(EvalSuite.system.is_(False))).all():
        db.delete(s)
    for a in db.scalars(select(CustomAgent).where(CustomAgent.id.like("custom-demo-%"))).all():
        db.delete(a)
    db.commit()


def main() -> None:
    init_db()
    with SessionLocal() as db:
        seed_defaults(db)
        if "--reset" in sys.argv:
            reset(db)
            log("previous data cleared")
        elif db.scalar(select(ShowcaseItem)) is not None or db.scalar(select(func_count())) > 200:
            log("demo data already present; run with --reset to rebuild")
            return
        users = seed_users(db)
        log(f"usage: {seed_usage(db, users)} ledger rows over 30 days for {len(users)} people")
    runs = seed_runs()
    with SessionLocal() as db:
        users = {u.id: u for u in db.scalars(select(User)).all()}
        space, agents = seed_knowledge_and_agents(db, users)
        log(f"knowledge space '{space.name}' with {space.doc_count} documents, {len(agents)} wizard agents")
        seed_evals(db, agents)
        seed_community(db, users, runs, agents)
    print("Demo tenant ready. Sign in as any of the ten people; Satya Bonda is the administrator.", file=sys.stderr)


def func_count():
    from sqlalchemy import func

    return func.count(UsageEvent.id)


if __name__ == "__main__":
    main()
