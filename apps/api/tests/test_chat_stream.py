import json


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.replace("\r\n", "\n").strip().split("\n\n"):
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        if event and data is not None:
            events.append((event, json.loads(data)))
    return events


def test_chat_stream_persists_and_meters(client, headers):
    with client.stream(
        "POST", "/v1/chat/stream", headers=headers,
        json={"model": "claude-sonnet-5", "messages": [{"role": "user", "content": "Hello ledger"}]},
    ) as r:
        assert r.status_code == 200
        events = parse_sse("".join(r.iter_text()))

    kinds = [e for e, _ in events]
    assert kinds[0] == "meta" and "delta" in kinds and "usage" in kinds and kinds[-1] == "done"
    usage = next(d for e, d in events if e == "usage")
    assert usage["tokens_in"] > 0 and usage["tokens_out"] > 0
    assert usage["cost_usd"] > 0 and usage["model"] == "claude-sonnet-5"
    text = "".join(d["text"] for e, d in events if e == "delta")
    assert "Hello ledger" in text

    conv_id = events[0][1]["conversation_id"]
    conv = client.get(f"/v1/conversations/{conv_id}", headers=headers).json()
    assert conv["title"] == "Hello ledger"
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert conv["messages"][1]["cost_usd"] == usage["cost_usd"]

    summary = client.get("/v1/usage/summary?days=7", headers=headers).json()
    assert summary["requests"] >= 1 and summary["spend_window_usd"] >= usage["cost_usd"]
    assert any(m["model"] == "claude-sonnet-5" for m in summary["by_model"])


def test_compare_does_not_persist_but_meters(client, headers):
    before = client.get("/v1/usage/summary?days=7", headers=headers).json()["requests"]
    with client.stream(
        "POST", "/v1/chat/stream", headers=headers,
        json={"model": "gpt-5.6-terra", "messages": [{"role": "user", "content": "compare me"}], "persist": False, "feature": "compare"},
    ) as r:
        events = parse_sse("".join(r.iter_text()))
    meta = next(d for e, d in events if e == "meta")
    assert meta["conversation_id"] is None
    after = client.get("/v1/usage/summary?days=7", headers=headers).json()
    assert after["requests"] == before + 1
    assert any(f["feature"] == "compare" for f in after["by_feature"])


def test_conversation_search_and_patch(client, headers):
    listing = client.get("/v1/conversations?q=ledger", headers=headers).json()["conversations"]
    assert listing and listing[0]["title"] == "Hello ledger"
    cid = listing[0]["id"]
    patched = client.patch(f"/v1/conversations/{cid}", headers=headers, json={"tags": ["finance"], "pinned": True}).json()
    assert patched["tags"] == ["finance"] and patched["pinned"] is True
    assert client.get("/v1/conversations?tag=finance", headers=headers).json()["conversations"][0]["id"] == cid
    other = {**headers, "X-User-Id": "u2", "X-User-Email": "priya@playground.local"}
    assert client.get(f"/v1/conversations/{cid}", headers=other).status_code == 404
