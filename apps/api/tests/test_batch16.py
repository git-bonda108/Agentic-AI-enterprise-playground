"""Batch 16: datasets with schema, provenance and export; trusted sources; cost drill-down with filters, ledger rows and CSV; console hours."""

import csv
import io
from datetime import UTC, datetime

from app.datasets import SOURCES, columns_for


def test_datasets_carry_columns_provenance_snippet_and_export_links(client, headers):
    body = client.get("/v1/data", headers=headers).json()["datasets"]
    assert len(body) == 8
    for d in body:
        assert d["columns"] and all(c["name"] and c["type"] for c in d["columns"]), d["id"]
        assert d["licence"]["url"].startswith("https://") and d["shape"] in ("table", "keyed")
        assert d["snippet"].startswith("import playground") and d["id"] in d["snippet"]
        assert d["download"]["csv"] == f"/v1/data/{d['id']}/download?format=csv"
        assert d["used_by"]
    sales = next(d for d in body if d["id"] == "sales")
    assert [c["name"] for c in sales["columns"]] == ["date", "region", "product", "units", "revenue"]
    assert {c["name"]: c["type"] for c in sales["columns"]} == {"date": "date", "region": "string", "product": "string", "units": "integer", "revenue": "number"}
    assert sales["modeled_on"]["name"].startswith("AdventureWorks") and sales["notebook"] == "data-with-pandas"
    assert columns_for([{"a": 1, "b": True, "c": [1]}, {"a": 2, "d": "x"}]) == [
        {"name": "a", "type": "integer", "example": 1}, {"name": "b", "type": "boolean", "example": True}, {"name": "c", "type": "list", "example": "[1]"}, {"name": "d", "type": "string", "example": "x"},
    ]


def test_dataset_download_as_csv_and_json_with_a_filename(client, headers):
    r = client.get("/v1/data/sales/download?format=csv", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == 'attachment; filename="sales.csv"'
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert rows and list(rows[0]) == ["date", "region", "product", "units", "revenue"]
    j = client.get("/v1/data/invoices/download?format=json", headers=headers)
    assert j.status_code == 200 and j.headers["content-disposition"] == 'attachment; filename="invoices.json"' and isinstance(j.json(), list)
    keyed = client.get("/v1/data/research_corpus/download?format=csv", headers=headers)
    assert keyed.status_code == 200 and keyed.text.startswith("key,")
    assert client.get("/v1/data/nope/download", headers=headers).status_code == 404
    assert client.get("/v1/data/sales/download?format=xml", headers=headers).status_code == 422


def test_trusted_sources_are_curated_with_loaders(client, headers):
    body = client.get("/v1/data/sources", headers=headers).json()["sources"]
    assert body == SOURCES and len(body) >= 12
    ids = [s["id"] for s in body]
    assert len(ids) == len(set(ids)) and {"kaggle", "huggingface", "uci", "openml", "datagov", "worldbank"} <= set(ids)
    for s in body:
        assert s["url"].startswith("https://") and s["docs"].startswith("https://") and s["licence"] and s["good_for"]
        if s["install"]:
            assert s["install"].startswith("%pip install") and s["python"]
    kaggle = next(s for s in body if s["id"] == "kaggle")
    assert "kagglehub" in kaggle["install"] and "dataset_download" in kaggle["python"]


def _run_blueprint(client, headers) -> dict:
    r = client.post("/v1/runs", json={"blueprint_id": "knowledge-qa", "input": {"question": "What is the hotel limit per night?"}, "wait": True}, headers=headers)
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_breakdown_filters_stack_and_the_blueprint_layer_names_the_run(client, headers):
    _run_blueprint(client, headers)
    client.post("/v1/notebooks/heartbeat", json={"path": "/v1/notebooks/blank.ipynb", "mode": "browser"}, headers=headers)
    by_bp = client.get("/v1/usage/breakdown?days=1&by=blueprint", headers=headers).json()
    assert by_bp["filters"] == {} and any(r["label"] == "Knowledge Q&A" and r["key"] == "knowledge-qa" for r in by_bp["rows"])
    assert {"tokens_in", "tokens_out", "tokens_cached"} <= set(by_bp["totals"])
    narrowed = client.get("/v1/usage/breakdown?days=1&by=feature&blueprint_id=knowledge-qa", headers=headers).json()
    assert narrowed["filters"] == {"blueprint_id": "knowledge-qa"}
    assert [r["key"] for r in narrowed["rows"]] == ["agent"]
    assert narrowed["totals"]["requests"] < client.get("/v1/usage/breakdown?days=1&by=feature", headers=headers).json()["totals"]["requests"]
    today = datetime.now(UTC).date().isoformat()
    by_day = client.get(f"/v1/usage/breakdown?days=1&by=model&day={today}&feature=notebook", headers=headers).json()
    assert by_day["rows"] and all(r["key"].startswith("editor-") for r in by_day["rows"])
    empty = client.get("/v1/usage/breakdown?days=1&by=model&department=Nowhere", headers=headers).json()
    assert empty["rows"] == [] and empty["totals"]["requests"] == 0
    csv_text = client.get("/v1/usage/breakdown?days=1&by=feature&format=csv", headers=headers)
    assert csv_text.headers["content-type"].startswith("text/csv") and csv_text.headers["content-disposition"] == 'attachment; filename="cost-by-feature-1d.csv"'
    rows = list(csv.DictReader(io.StringIO(csv_text.text)))
    assert rows and rows[0]["layer"] == "feature" and "cost_usd" in rows[0] and "latency_ms" not in rows[0]


def test_ledger_rows_are_paged_filtered_scoped_and_exportable(client, headers):
    run = _run_blueprint(client, headers)
    page = client.get("/v1/usage/events?days=1&limit=2&blueprint_id=knowledge-qa", headers=headers).json()
    assert page["total"] >= 1 and len(page["rows"]) <= 2 and page["filters"] == {"blueprint_id": "knowledge-qa"}
    row = page["rows"][0]
    assert row["blueprint"] == "Knowledge Q&A" and row["feature"] == "agent" and row["user"] and row["created_at"].endswith("+00:00")
    assert {"tokens_in", "tokens_out", "tokens_cached", "cost_usd", "latency_ms", "status", "key_source", "routed", "run_id", "trace_id"} <= set(row)
    assert any(r["run_id"] == run["id"] for r in client.get("/v1/usage/events?days=1&limit=500&blueprint_id=knowledge-qa", headers=headers).json()["rows"])
    second = client.get("/v1/usage/events?days=1&limit=1&offset=1&blueprint_id=knowledge-qa", headers=headers).json()
    assert second["offset"] == 1 and (second["rows"] == [] or second["rows"][0]["id"] != row["id"])
    # Newest first.
    times = [r["created_at"] for r in client.get("/v1/usage/events?days=1&limit=50", headers=headers).json()["rows"]]
    assert times == sorted(times, reverse=True)
    # An explorer only sees their own rows.
    explorer = {**headers, "X-User-Id": "u-explorer-16", "X-User-Email": "explorer16@example.com", "X-User-Name": "Explorer Sixteen", "X-User-Role": "explorer"}
    mine = client.get("/v1/usage/events?days=1", headers=explorer).json()
    assert mine["scope"] == "me" and all(r["user"] == "Explorer Sixteen" for r in mine["rows"])
    exported = client.get("/v1/usage/events?days=1&format=csv&blueprint_id=knowledge-qa", headers=headers)
    assert exported.headers["content-disposition"] == 'attachment; filename="ledger-1d.csv"'
    assert next(iter(csv.DictReader(io.StringIO(exported.text))))["blueprint"] == "Knowledge Q&A"


def test_console_summary_reports_hours_per_feature_bucket(client, headers):
    # A fresh explorer so the session holds only this test's events (a shared session would round a single heartbeat's share to zero).
    me = {**headers, "X-User-Id": "u-hours-16", "X-User-Email": "hours16@example.com", "X-User-Name": "Hours Sixteen", "X-User-Role": "explorer"}
    _run_blueprint(client, me)
    client.post("/v1/notebooks/heartbeat", json={"path": "/v1/notebooks/blank.ipynb", "mode": "sandbox"}, headers=me)
    hours = client.get("/v1/usage/summary?days=7", headers=me).json()["hours"]
    assert hours["days"] == 7 and set(hours["window"]) == {"chat", "agent", "notebook", "sdk", "other", "total"}
    assert set(hours["previous"]) == set(hours["window"]) and set(hours["people"]) == {"chat", "agent", "notebook", "sdk"}
    assert hours["window"]["agent"] > 0 and hours["window"]["total"] >= hours["window"]["agent"]
    assert hours["people"] == {"chat": 0, "agent": 1, "notebook": 1, "sdk": 0}
    assert hours["previous"]["total"] == 0
    # Leaders see everyone: the organisation total covers this person's hours too.
    org = client.get("/v1/usage/summary?days=7", headers=headers).json()["hours"]
    assert org["window"]["total"] >= hours["window"]["total"] and org["people"]["agent"] >= 1
