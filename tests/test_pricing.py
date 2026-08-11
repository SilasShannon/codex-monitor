from __future__ import annotations

from decimal import Decimal

from codex_monitor.models import TokenUsage
from codex_monitor.pricing import estimate_cost


def test_deterministic_api_equivalent_cost_and_cache_savings() -> None:
    usage = TokenUsage(
        input_tokens=3_100_000,
        cached_input_tokens=2_000_000,
        cache_write_input_tokens=100_000,
        output_tokens=500_000,
    )
    estimate = estimate_cost("gpt-5.6-sol", usage)
    assert estimate.available
    assert estimate.estimated_api_equivalent_cost == Decimal("21.625")
    assert estimate.estimated_without_cache == Decimal("30.500")
    assert estimate.estimated_cache_savings == Decimal("8.875")
    assert estimate.confidence == "HIGH"


def test_unknown_model_is_never_substituted() -> None:
    usage = TokenUsage(1, 0, 0, 1)
    estimate = estimate_cost("future-unknown-model", usage)
    assert not estimate.available
    assert estimate.confidence == "UNAVAILABLE"
    assert estimate.estimated_api_equivalent_cost is None
    assert "Pricing unknown" in (estimate.reason or "")


def test_missing_token_category_is_unavailable() -> None:
    estimate = estimate_cost("gpt-5.6-sol", TokenUsage(input_tokens=10, output_tokens=5))
    assert not estimate.available
    assert "token categories" in (estimate.reason or "")
