from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..database import Database
from ..models import TokenUsage
from ..pricing import estimate_cost


def _usage(row) -> TokenUsage:
    return TokenUsage(
        input_tokens=row["input_tokens"],
        cached_input_tokens=row["cached_input_tokens"],
        cache_write_input_tokens=row["cache_write_input_tokens"],
        output_tokens=row["output_tokens"],
        reasoning_output_tokens=row["reasoning_output_tokens"],
        total_tokens=row["total_tokens"],
        context_window=row["context_window"],
    )


def _timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def session_costs(db: Database, limit: int = 100) -> list[dict]:
    rows = db.connection.execute(
        """SELECT s.*,p.name project_name FROM sessions s
           LEFT JOIN projects p USING(project_key)
           ORDER BY COALESCE(s.last_activity,s.started_at) DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    result = []
    for row in rows:
        estimate = estimate_cost(row["model"], _usage(row), at=_timestamp(row["started_at"]))
        result.append({
            "session_id": row["session_id"],
            "project_name": row["project_name"],
            "model": row["model"],
            "started_at": row["started_at"],
            "last_activity": row["last_activity"],
            "tokens": row["total_tokens"],
            "estimated_api_equivalent_cost": (
                str(estimate.estimated_api_equivalent_cost)
                if estimate.estimated_api_equivalent_cost is not None else None
            ),
            "estimated_cache_savings": (
                str(estimate.estimated_cache_savings)
                if estimate.estimated_cache_savings is not None else None
            ),
            "confidence": estimate.confidence,
            "reason": estimate.reason,
        })
    return result


def cost_summary(db: Database, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    rows = session_costs(db, 100_000)
    totals = {"today": Decimal(0), "7_days": Decimal(0), "30_days": Decimal(0),
              "all_time": Decimal(0), "cache_savings": Decimal(0)}
    available = unavailable = 0
    for row in rows:
        value = row["estimated_api_equivalent_cost"]
        if value is None:
            unavailable += 1
            continue
        available += 1
        amount = Decimal(value)
        totals["all_time"] += amount
        totals["cache_savings"] += Decimal(row["estimated_cache_savings"] or 0)
        timestamp = _timestamp(row["started_at"] or row["last_activity"])
        if timestamp:
            age = now - timestamp.astimezone(timezone.utc)
            if timestamp.date() == now.date():
                totals["today"] += amount
            if age <= timedelta(days=7):
                totals["7_days"] += amount
            if age <= timedelta(days=30):
                totals["30_days"] += amount
    return {
        "terminology": "ESTIMATED API-EQUIVALENT COST",
        **{key: str(value) for key, value in totals.items()},
        "available_sessions": available,
        "unavailable_sessions": unavailable,
    }
