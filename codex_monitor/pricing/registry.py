from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from importlib.resources import files


@dataclass(frozen=True)
class PricingRecord:
    model: str
    effective_from: date
    input_per_million: Decimal
    cached_input_per_million: Decimal
    cache_write_per_million: Decimal
    output_per_million: Decimal
    source: str
    retrieved_at: str


class PricingRegistry:
    """Effective-dated pricing with exact model matching and no fallback guesses."""

    def __init__(self, records: list[PricingRecord], aliases: dict[str, str] | None = None):
        self.records = records
        self.aliases = aliases or {}

    @classmethod
    def bundled(cls) -> PricingRegistry:
        payload = json.loads(files("codex_monitor.pricing").joinpath("models.json").read_text())
        records: list[PricingRecord] = []
        aliases: dict[str, str] = {}
        for item in payload["records"]:
            records.append(PricingRecord(
                model=item["model"],
                effective_from=date.fromisoformat(item["effective_from"]),
                input_per_million=Decimal(item["input_per_million"]),
                cached_input_per_million=Decimal(item["cached_input_per_million"]),
                cache_write_per_million=Decimal(item["cache_write_per_million"]),
                output_per_million=Decimal(item["output_per_million"]),
                source=item["source"],
                retrieved_at=payload["retrieved_at"],
            ))
            for alias in item.get("aliases", []):
                aliases[alias] = item["model"]
        return cls(records, aliases)

    def find(self, model: str | None, at: date | datetime | None = None) -> PricingRecord | None:
        if not model:
            return None
        canonical = self.aliases.get(model, model)
        target = at.date() if isinstance(at, datetime) else (at or datetime.now(timezone.utc).date())
        matches = [
            record for record in self.records
            if record.model == canonical and record.effective_from <= target
        ]
        return max(matches, key=lambda record: record.effective_from) if matches else None
