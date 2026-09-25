from app.catalog import CATALOG, estimate_cost, get_model


def test_cost_uses_catalog_prices():
    # Sonnet 5: $2 in, $10 out per 1M tokens
    assert estimate_cost("claude-sonnet-5", 1_000_000, 0) == 2.0
    assert estimate_cost("claude-sonnet-5", 0, 1_000_000) == 10.0
    assert estimate_cost("claude-sonnet-5", 500_000, 100_000) == 2.0


def test_cached_tokens_billed_at_cached_rate():
    # Fable 5.1: $10 in, cached $0.25
    full = estimate_cost("claude-fable-5-1", 1_000_000, 0, tokens_cached=0)
    cached = estimate_cost("claude-fable-5-1", 1_000_000, 0, tokens_cached=1_000_000)
    assert full == 10.0
    assert cached == 0.25


def test_unknown_model_costs_nothing():
    assert estimate_cost("nope", 1000, 1000) == 0.0


def test_catalog_ids_are_unique_and_priced():
    ids = [m.id for m in CATALOG]
    assert len(ids) == len(set(ids))
    for m in CATALOG:
        assert m.input_per_m >= 0 and m.output_per_m >= 0
        assert get_model(m.id) is m
