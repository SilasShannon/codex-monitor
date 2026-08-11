from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ..models import TokenUsage
from .registry import PricingRegistry

MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class CostEstimate:
    available: bool
    estimated_api_equivalent_cost: Decimal | None
    estimated_without_cache: Decimal | None
    estimated_cache_savings: Decimal | None
    confidence: str
    reason: str | None
    model: str | None
    pricing_source: str | None
    pricing_effective_from: str | None


def estimate_cost(
    model: str | None,
    usage: TokenUsage,
    *,
    at: date | datetime | None = None,
    registry: PricingRegistry | None = None,
) -> CostEstimate:
    registry = registry or PricingRegistry.bundled()
    pricing = registry.find(model, at)
    if pricing is None:
        return CostEstimate(False, None, None, None, "UNAVAILABLE",
                            f"Pricing unknown for model {model or '<unknown>'}", model, None, None)
    values = (usage.input_tokens, usage.cached_input_tokens, usage.cache_write_input_tokens,
              usage.output_tokens)
    if any(value is None for value in values):
        return CostEstimate(False, None, None, None, "UNAVAILABLE",
                            "One or more required token categories are unavailable",
                            model, pricing.source, pricing.effective_from.isoformat())

    input_tokens = Decimal(max(usage.input_tokens or 0, 0))
    cached_tokens = Decimal(max(usage.cached_input_tokens or 0, 0))
    cache_write_tokens = Decimal(max(usage.cache_write_input_tokens or 0, 0))
    output_tokens = Decimal(max(usage.output_tokens or 0, 0))
    # Codex input_tokens is inclusive: total_tokens == input_tokens + output_tokens.
    # Cached reads and writes are billable subcategories of input, not additions.
    fresh_input_tokens = max(input_tokens - cached_tokens - cache_write_tokens, Decimal(0))
    estimated = (
        fresh_input_tokens * pricing.input_per_million
        + cached_tokens * pricing.cached_input_per_million
        + cache_write_tokens * pricing.cache_write_per_million
        + output_tokens * pricing.output_per_million
    ) / MILLION
    without_cache = (
        input_tokens * pricing.input_per_million
        + output_tokens * pricing.output_per_million
    ) / MILLION
    return CostEstimate(
        True, estimated, without_cache, without_cache - estimated, "HIGH", None, model,
        pricing.source, pricing.effective_from.isoformat(),
    )
