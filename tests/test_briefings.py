from __future__ import annotations

import json
from dataclasses import replace

from codex_monitor.briefings import active_briefings, session_briefing
from codex_monitor.indexer import Indexer


def test_session_briefing_uses_only_observed_evidence(config, db, codex_root) -> None:
    path = next((codex_root / "sessions").rglob("*.jsonl"))
    with path.open("a") as handle:
        handle.write(json.dumps({
            "timestamp": "2026-08-10T12:00:10Z", "type": "event_msg",
            "payload": {"type": "agent_message", "message": "The parser tests pass now."},
        }) + "\n")
    Indexer(replace(config, log_user_prompts=True), db).scan()
    briefing = session_briefing(db, "session-test-1")
    assert briefing
    assert briefing["request"] == "Build a safe parser"
    assert briefing["latest_visible_update"] == "The parser tests pass now."
    assert briefing["tests"][0]["command"] == "pytest"
    assert briefing["tests"][0]["success"] is True
    assert briefing["files"][0]["action"] == "created"
    assert any(item["name"] == "Automated testing" for item in briefing["concepts"])
    assert "hidden reasoning" in briefing["evidence_note"]


def test_active_briefings_returns_recent_sessions(config, db) -> None:
    next((config.data_roots[0] / "sessions").rglob("*.jsonl")).touch()
    Indexer(config, db).scan()
    results = active_briefings(db)
    assert len(results) == 1
    assert results[0]["session_id"] == "session-test-1"
