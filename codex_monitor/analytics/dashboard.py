from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..database import Database
from ..pricing import estimate_cost
from .costs import _timestamp, _usage


def _session_rows(db: Database):
    return db.connection.execute(
        """SELECT s.*,p.name project_name FROM sessions s
           LEFT JOIN projects p USING(project_key)"""
    ).fetchall()


def usage_timeseries(db: Database, days: int = 30, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    start = now.date() - timedelta(days=max(days - 1, 0))
    buckets = {
        start + timedelta(days=offset): {
            "input_tokens": 0, "cached_input_tokens": 0, "cache_write_input_tokens": 0,
            "output_tokens": 0, "total_tokens": 0, "estimated_api_equivalent_cost": Decimal(0),
            "priced_sessions": 0, "unpriced_sessions": 0,
        }
        for offset in range(days)
    }
    for row in _session_rows(db):
        timestamp = _timestamp(row["started_at"] or row["last_activity"])
        if not timestamp or timestamp.date() not in buckets:
            continue
        bucket = buckets[timestamp.date()]
        for key in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                    "output_tokens", "total_tokens"):
            bucket[key] += row[key] or 0
        estimate = estimate_cost(row["model"], _usage(row), at=timestamp)
        if estimate.estimated_api_equivalent_cost is None:
            bucket["unpriced_sessions"] += 1
        else:
            bucket["priced_sessions"] += 1
            bucket["estimated_api_equivalent_cost"] += estimate.estimated_api_equivalent_cost
    return [
        {"date": day.isoformat(), **values,
         "estimated_api_equivalent_cost": str(values["estimated_api_equivalent_cost"])}
        for day, values in sorted(buckets.items())
    ]


def usage_breakdown(
    db: Database, dimension: str = "project", limit: int = 20, sort_by: str = "tokens"
) -> list[dict]:
    if dimension not in {"project", "model", "session"}:
        raise ValueError("dimension must be project, model, or session")
    if sort_by not in {"tokens", "cost"}:
        raise ValueError("sort must be tokens or cost")
    buckets: dict[str, dict] = defaultdict(lambda: {
        "sessions": 0, "input_tokens": 0, "cached_input_tokens": 0,
        "output_tokens": 0, "total_tokens": 0,
        "estimated_api_equivalent_cost": Decimal(0), "unpriced_sessions": 0,
    })
    for row in _session_rows(db):
        key = {
            "project": row["project_name"] or "Unassigned",
            "model": row["model"] or "Unknown",
            "session": row["session_id"],
        }[dimension]
        bucket = buckets[key]
        bucket["sessions"] += 1
        for field in ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens"):
            bucket[field] += row[field] or 0
        timestamp = _timestamp(row["started_at"] or row["last_activity"])
        estimate = estimate_cost(row["model"], _usage(row), at=timestamp)
        if estimate.estimated_api_equivalent_cost is None:
            bucket["unpriced_sessions"] += 1
        else:
            bucket["estimated_api_equivalent_cost"] += estimate.estimated_api_equivalent_cost
    result = [
        {"name": name, **values,
         "estimated_api_equivalent_cost": str(values["estimated_api_equivalent_cost"])}
        for name, values in buckets.items()
    ]
    sort_key = "total_tokens" if sort_by == "tokens" else "estimated_api_equivalent_cost"
    return sorted(result, key=lambda item: Decimal(str(item[sort_key])), reverse=True)[:limit]
