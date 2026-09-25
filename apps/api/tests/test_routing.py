import json

from app.router import classify, route
from tests.routing_set import ROUTING_SET


def test_routing_set_has_one_hundred_prompts():
    assert len(ROUTING_SET) == 100


def test_classifier_accuracy_at_least_ninety_percent():
    correct = 0
    misses = []
    for prompt, expected in ROUTING_SET:
        tier, _ = classify(prompt)
        if tier == expected:
            correct += 1
        else:
            misses.append((expected, tier, prompt[:70]))
    accuracy = correct / len(ROUTING_SET)
    assert accuracy >= 0.9, f"accuracy {accuracy:.2f}; misses: {misses}"


def test_route_prefers_cheapest_model_in_tier_and_reports_savings():
    decision = route("Translate 'hello' to Spanish.")
    assert decision is not None
    assert decision.tier == "Economy"
    assert decision.est_cost_usd < decision.est_baseline_cost_usd
    assert decision.est_savings_pct > 50


def test_smart_chat_resolves_model_and_records_savings(client, headers):
    with client.stream(
        "POST", "/v1/chat/stream", headers=headers,
        json={"model": "smart", "messages": [{"role": "user", "content": "Translate 'good night' to Italian."}], "persist": False, "feature": "chat"},
    ) as r:
        events = []
        for block in "".join(r.iter_text()).replace("\r\n", "\n").split("\n\n"):
            ev, data = None, None
            for line in block.splitlines():
                if line.startswith("event:"):
                    ev = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:].strip())
            if ev:
                events.append((ev, data))
    meta = next(d for e, d in events if e == "meta")
    assert meta["routed"] is True and meta["routed_tier"] == "Economy" and meta["model"] != "smart"
    usage = next(d for e, d in events if e == "usage")
    assert usage["routed"] is True and usage["savings_usd"] >= 0
    body = client.get("/v1/usage/breakdown?days=7&by=model", headers=headers).json()
    assert body["totals"]["routed_requests"] >= 1


def test_route_preview_endpoint(client, headers):
    body = client.post("/v1/route/preview", headers=headers, json={"prompt": "Design a system architecture and analyze the trade-offs."}).json()
    assert body["enabled"] is True
    assert body["decision"]["tier"] == "Premium"
    assert "reason" in body["decision"]
