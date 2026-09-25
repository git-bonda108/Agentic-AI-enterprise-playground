"""Mock datasets. Generated deterministically on first use, modeled on public sets (AdventureWorks, Voxel51 invoices, CUAD, Bitext)."""

from __future__ import annotations

import csv
import json
import random

from app.config import API_DIR

DATA_DIR = API_DIR / "data"

VENDORS = [
    ("V-100", "Northwind Components", "NET30", 0.0), ("V-101", "Contoso Logistics", "NET45", 0.02), ("V-102", "Fabrikam Steel", "NET30", 0.0),
    ("V-103", "Adventure Works Cycles", "NET60", 0.05), ("V-104", "Tailspin Freight", "NET30", 0.0),
]
PRODUCTS = ["Mountain-100 Black", "Road-250 Red", "Touring-1000 Blue", "HL Road Frame", "Sport-100 Helmet", "Water Bottle", "Bike Wash", "Cable Lock"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]

POLICIES = [
    {"id": "POL-001", "title": "Travel and expense policy", "body": "Employees may claim economy airfare, hotel up to 220 USD per night in major cities and 150 USD elsewhere, and meals up to 60 USD per day with receipts. Claims must be filed within 30 days of travel. Business class requires director approval for flights over 8 hours."},
    {"id": "POL-002", "title": "Procurement thresholds", "body": "Purchases under 5,000 USD need a manager approval. Purchases from 5,000 to 50,000 USD require three quotes and a purchase order. Above 50,000 USD a tender and legal review are mandatory. Single-source justification must be documented."},
    {"id": "POL-003", "title": "Invoice matching", "body": "Invoices are matched three ways: invoice, purchase order and goods receipt. A tolerance of 2 percent or 100 USD, whichever is lower, is accepted. Invoices without a purchase order number are returned to the vendor. Duplicate invoice numbers are rejected automatically."},
    {"id": "POL-004", "title": "Remote work", "body": "Employees may work remotely up to three days per week with manager agreement. Equipment stipend is 500 USD per year. Core collaboration hours are 10:00 to 15:00 local time. Working from another country for more than 30 days needs HR and tax approval."},
    {"id": "POL-005", "title": "Data classification", "body": "Data is classified as Public, Internal, Confidential or Restricted. Restricted data such as payroll and health records may not be pasted into external AI tools. Confidential data may be used in the governed AI playground with an approved policy. Public data has no restrictions."},
    {"id": "POL-006", "title": "AI usage policy", "body": "Employees may use the Enterprise AI Playground for drafting, analysis and research. Outputs used in decisions must be reviewed by a human. Model choice is governed by role policy. Every request is metered and visible to the person and their manager."},
    {"id": "POL-007", "title": "Vendor onboarding", "body": "New vendors must supply a tax certificate, bank confirmation letter and signed code of conduct. Master data changes require dual approval. Vendors inactive for 18 months are archived."},
    {"id": "POL-008", "title": "Learning and development", "body": "Every employee has a 1,200 USD annual learning budget. Certifications in AI, cloud and data are reimbursed at 100 percent on passing. Managers approve learning plans each quarter; time for learning is capped at four hours per week."},
    {"id": "POL-009", "title": "Contract review", "body": "Contracts above 25,000 USD require legal review. Auto-renewal clauses must be flagged 90 days before renewal. Liability caps below one year of fees need CFO sign-off. Governing law defaults to the entity's home jurisdiction."},
    {"id": "POL-010", "title": "Information security basics", "body": "Multi-factor authentication is mandatory. Passwords rotate every 180 days or on compromise. Report phishing to security within one hour. Personal devices need mobile device management before accessing email."},
]

COMPANIES = {
    "Apple": [("Apple designs and sells consumer electronics, software and services; the iPhone is its largest product line.", "https://www.apple.com/newsroom/"), ("Apple reported services revenue growth driven by App Store, iCloud and subscriptions.", "https://investor.apple.com/"), ("Apple's supply chain concentrates final assembly in Asia with growing capacity in India.", "https://www.apple.com/supplier-responsibility/")],
    "Tesla": [("Tesla builds electric vehicles and energy storage; the Model Y is its highest volume vehicle.", "https://ir.tesla.com/"), ("Tesla's energy storage deployments grew faster than vehicle deliveries in recent quarters.", "https://www.tesla.com/energy"), ("Tesla operates gigafactories in the United States, China and Germany.", "https://www.tesla.com/manufacturing")],
    "Microsoft": [("Microsoft's cloud segment, led by Azure, is the largest contributor to revenue growth.", "https://www.microsoft.com/investor/"), ("Microsoft Foundry offers a catalog of models from Microsoft, OpenAI, Anthropic and open-source providers.", "https://azure.microsoft.com/en-us/products/ai-foundry/"), ("Microsoft 365 Copilot is sold as an add-on to enterprise Microsoft 365 plans.", "https://www.microsoft.com/microsoft-365/copilot")],
    "Anthropic": [("Anthropic develops the Claude family of models and offers them through its API and cloud partners.", "https://www.anthropic.com/"), ("Claude models are available on Amazon Bedrock, Google Cloud Vertex AI and Microsoft Foundry.", "https://platform.claude.com/docs/"), ("Anthropic publishes a Responsible Scaling Policy governing model releases.", "https://www.anthropic.com/responsible-scaling-policy")],
}

LEARNING_REFS = {
    "SQL": [("SQL for Data Analysis, Mode Analytics", "https://mode.com/sql-tutorial/"), ("PostgreSQL official tutorial", "https://www.postgresql.org/docs/current/tutorial.html"), ("Advanced SQL window functions, YouTube", "https://www.youtube.com/results?search_query=sql+window+functions")],
    "Prompt engineering": [("Anthropic prompt engineering guide", "https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview"), ("OpenAI prompt engineering guide", "https://developers.openai.com/api/docs/guides/prompt-engineering"), ("DeepLearning.AI short course", "https://www.deeplearning.ai/short-courses/")],
    "Agentic AI": [("LangGraph documentation", "https://docs.langchain.com/oss/python/langgraph/overview"), ("OpenAI Agents SDK", "https://openai.github.io/openai-agents-python/"), ("Microsoft Agent Framework", "https://learn.microsoft.com/en-us/agent-framework/overview")],
    "Data privacy": [("GDPR essentials, European Commission", "https://commission.europa.eu/law/law-topic/data-protection_en"), ("NIST Privacy Framework", "https://www.nist.gov/privacy-framework"), ("Data classification basics, YouTube", "https://www.youtube.com/results?search_query=data+classification+basics")],
    "Financial analysis": [("Corporate Finance Institute, free courses", "https://corporatefinanceinstitute.com/"), ("Khan Academy finance", "https://www.khanacademy.org/economics-finance-domain"), ("Earned value management primer", "https://www.pmi.org/learning/library/earned-value-management")],
}

DRAFTS = [
    {"id": "DRAFT-1", "title": "Supplier price increase notice", "text": "Dear supplier, from next month we will pay all invoices net 90 regardless of contract terms. We may also deduct 5 percent for early payment at our discretion. Thank you for your partnership."},
    {"id": "DRAFT-2", "title": "AI playground announcement", "text": "We are launching the Enterprise AI Playground. Anyone can use any model with any data, including customer records. There are no limits. Please share your best prompts on the intranet."},
    {"id": "DRAFT-3", "title": "Quarterly training update", "text": "This quarter 240 employees completed the AI foundations course, up from 150 last quarter. The satisfaction score was 4.6 of 5. Next quarter we add an agentic AI track with hands-on labs and evaluation exercises."},
]


def _ensure_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    inv_path, po_path, con_path, sales_path = DATA_DIR / "invoices.json", DATA_DIR / "purchase_orders.json", DATA_DIR / "contracts.json", DATA_DIR / "sales.csv"
    if not po_path.exists():
        pos = []
        for i in range(24):
            vid, vname, terms, _ = VENDORS[i % len(VENDORS)]
            amount = round(rng.uniform(800, 42000), 2)
            pos.append({"po_number": f"PO-{5000 + i}", "vendor_id": vid, "vendor": vname, "amount": amount, "currency": "USD", "issued": f"2026-0{1 + i % 8}-{10 + i % 15:02d}", "terms": terms, "description": rng.choice(PRODUCTS) + " x" + str(rng.randint(5, 400))})
        po_path.write_text(json.dumps(pos, indent=2))
    if not con_path.exists():
        contracts = [
            {"contract_id": f"CTR-{i + 1}", "vendor_id": vid, "vendor": vname, "payment_terms": terms, "early_payment_discount": disc, "annual_cap": 250000.0, "auto_renewal": i % 2 == 0, "liability_cap_months": 12 if i != 3 else 6, "governing_law": "Delaware", "clause_types": ["Payment terms", "Termination for convenience", "Limitation of liability", "Auto-renewal" if i % 2 == 0 else "Fixed term"]}
            for i, (vid, vname, terms, disc) in enumerate(VENDORS)
        ]
        con_path.write_text(json.dumps(contracts, indent=2))
    if not inv_path.exists():
        pos = json.loads(po_path.read_text())
        invoices = []
        for i in range(20):
            po = pos[i]
            inv = {"invoice_number": f"INV-{9000 + i}", "vendor_id": po["vendor_id"], "vendor": po["vendor"], "po_number": po["po_number"], "amount": po["amount"], "currency": "USD", "invoice_date": po["issued"].replace("-10", "-20"), "due_terms": po["terms"], "lines": [{"sku": po["description"].split(" x")[0], "qty": int(po["description"].split(" x")[1]), "unit_price": round(po["amount"] / int(po["description"].split(" x")[1]), 2)}]}
            # seeded anomalies
            if i == 2:
                inv["amount"] = round(po["amount"] * 1.12, 2)  # over PO by 12 percent
            if i == 5:
                inv["po_number"] = None  # missing PO
            if i == 7:
                inv["invoice_number"] = "INV-9003"  # duplicate number
            if i == 9:
                inv["due_terms"] = "NET15"  # terms differ from contract
            if i == 12:
                inv["invoice_date"] = "2025-12-01"  # dated before the PO
            if i == 15:
                inv["vendor_id"] = "V-999"  # unknown vendor
            invoices.append(inv)
        inv_path.write_text(json.dumps(invoices, indent=2))
    if not sales_path.exists():
        with sales_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "region", "product", "units", "revenue"])
            for m in range(1, 13):
                for region in REGIONS:
                    for product in PRODUCTS:
                        units = rng.randint(5, 220)
                        price = {"Mountain-100 Black": 3400, "Road-250 Red": 2400, "Touring-1000 Blue": 2100, "HL Road Frame": 1400, "Sport-100 Helmet": 35, "Water Bottle": 5, "Bike Wash": 8, "Cable Lock": 25}[product]
                        w.writerow([f"2025-{m:02d}-15", region, product, units, round(units * price * rng.uniform(0.9, 1.05), 2)])
    for name, payload in (("policies.json", POLICIES), ("research_corpus.json", COMPANIES), ("learning_refs.json", LEARNING_REFS), ("drafts.json", DRAFTS)):
        path = DATA_DIR / name
        if not path.exists():
            path.write_text(json.dumps(payload, indent=2))


def load_json(name: str):
    _ensure_files()
    return json.loads((DATA_DIR / name).read_text())


def load_csv(name: str) -> list[dict]:
    _ensure_files()
    with (DATA_DIR / name).open() as f:
        return list(csv.DictReader(f))


DATASETS = [
    {"id": "invoices", "file": "invoices.json", "title": "Supplier invoices", "source": "Synthetic, modeled on the Voxel51 invoice OCR set (ODbL)", "used_by": ["doc-reconciliation"]},
    {"id": "purchase_orders", "file": "purchase_orders.json", "title": "Purchase orders", "source": "Synthetic, AdventureWorks-style products", "used_by": ["doc-reconciliation"]},
    {"id": "contracts", "file": "contracts.json", "title": "Vendor contracts", "source": "Synthetic, CUAD clause taxonomy (CC-BY-4.0)", "used_by": ["doc-reconciliation"]},
    {"id": "sales", "file": "sales.csv", "title": "Monthly sales", "source": "Synthetic, AdventureWorks-style", "used_by": ["data-analyst"]},
    {"id": "policies", "file": "policies.json", "title": "Company policies", "source": "Synthetic", "used_by": ["knowledge-qa"]},
    {"id": "research_corpus", "file": "research_corpus.json", "title": "Offline research corpus", "source": "Public facts with source links", "used_by": ["sage-lens"]},
    {"id": "learning_refs", "file": "learning_refs.json", "title": "Learning references", "source": "Public course and documentation links", "used_by": ["learning-path"]},
    {"id": "drafts", "file": "drafts.json", "title": "Sample drafts", "source": "Synthetic", "used_by": ["review-panel"]},
]


def dataset_catalog() -> list[dict]:
    _ensure_files()
    out = []
    for d in DATASETS:
        rows = load_csv(d["file"]) if d["file"].endswith(".csv") else load_json(d["file"])
        if isinstance(rows, dict):
            preview = [{"key": k, "items": len(v)} for k, v in rows.items()]
            count = len(rows)
        else:
            preview = rows[:5]
            count = len(rows)
        out.append({**d, "rows": count, "preview": preview})
    return out
