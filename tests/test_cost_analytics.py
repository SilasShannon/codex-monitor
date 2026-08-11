from __future__ import annotations

from codex_monitor.analytics import cost_summary, session_costs
from codex_monitor.indexer import Indexer


def test_unknown_fixture_model_is_unavailable(config, db) -> None:
    Indexer(config, db).scan()
    costs = session_costs(db)
    assert costs[0]["estimated_api_equivalent_cost"] is None
    assert costs[0]["confidence"] == "UNAVAILABLE"
    summary = cost_summary(db)
    assert summary["all_time"] == "0"
    assert summary["unavailable_sessions"] == 1
