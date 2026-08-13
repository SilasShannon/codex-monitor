from __future__ import annotations

import json
from dataclasses import replace

from codex_monitor.briefings import _status, active_briefings, recent_briefings, session_briefing
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
    assert briefing["phase"] == "Verifying"
    assert briefing["activity_story"][0] == "Current observed phase: Verifying."
    assert "tests protect" in briefing["questions_to_ask"][1]
    assert any(item["name"] == "Automated testing" for item in briefing["concepts"])
    assert "hidden reasoning" in briefing["evidence_note"]


def test_active_briefings_returns_recent_sessions(config, db) -> None:
    next((config.data_roots[0] / "sessions").rglob("*.jsonl")).touch()
    Indexer(config, db).scan()
    results = active_briefings(db)
    assert len(results) == 1
    assert results[0]["session_id"] == "session-test-1"


def test_recent_briefings_include_inactive_sessions(config, db) -> None:
    Indexer(config, db).scan()
    results = recent_briefings(db, 1)
    assert len(results) == 1
    assert results[0]["session_id"] == "session-test-1"
    assert results[0]["phase"] == "Verifying"


def test_status_uses_structured_evidence_when_visible_text_is_unavailable() -> None:
    assert _status(True, None, None, "Verifying", [{"command": "pytest"}], [], []) == (
        "This session has recent activity. Observed phase: Verifying, based on 1 test command(s)."
    )
    assert _status(False, None, None, "Implementing", [], [{"path": "parser.py"}], []) == (
        "This session is not currently active. Observed phase: Implementing, based on activity in 1 file(s)."
    )
    assert _status(True, None, None, "Investigating", [], [], [{"name": "exec_command"}]) == (
        "This session has recent activity. Observed phase: Investigating, based on 1 tool call(s)."
    )


def test_status_keeps_evidence_limit_when_no_activity_is_observed() -> None:
    status = _status(False, None, None, "Waiting for evidence", [], [], [])
    assert "not enough visible evidence" in status
