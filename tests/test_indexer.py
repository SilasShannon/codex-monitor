from __future__ import annotations

import json
from pathlib import Path

from codex_monitor.indexer import Indexer


def rollout(codex_root: Path) -> Path:
    return next((codex_root / "sessions").rglob("*.jsonl"))


def test_index_builds_normalized_database(config, db) -> None:
    result = Indexer(config, db).scan()
    assert result == {"files": 1, "records": 10, "corrupt": 0}
    session = db.connection.execute("SELECT * FROM sessions").fetchone()
    assert session["session_id"] == "session-test-1"
    assert session["total_tokens"] == 120
    assert session["event_count"] == 10
    assert db.connection.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0] == 2
    assert db.connection.execute("SELECT COUNT(*) FROM unsupported_events").fetchone()[0] == 1
    assert db.connection.execute("SELECT action FROM file_activity").fetchone()[0] == "created"


def test_incremental_append_and_duplicate_deduplication(config, db, codex_root: Path) -> None:
    indexer = Indexer(config, db)
    indexer.scan()
    path = rollout(codex_root)
    record = {"timestamp": "2026-08-10T12:00:11Z", "type": "event_msg", "payload": {"type": "agent_message", "message": "done"}}
    encoded = json.dumps(record)
    with path.open("a") as handle:
        handle.write(encoded + "\n" + encoded + "\n")
    result = indexer.scan()
    assert result["records"] == 2
    assert db.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 11
    assert db.connection.execute("SELECT event_count FROM sessions").fetchone()[0] == 11


def test_partial_line_waits_for_completion(config, db, codex_root: Path) -> None:
    indexer = Indexer(config, db)
    indexer.scan()
    path = rollout(codex_root)
    with path.open("ab") as handle:
        handle.write(b'{"timestamp":"later","type":"event_msg"')
    assert indexer.scan()["records"] == 0
    with path.open("ab") as handle:
        handle.write(b',"payload":{"type":"agent_message","message":"ok"}}\n')
    assert indexer.scan()["records"] == 1


def test_corrupt_line_is_counted_and_following_line_survives(config, db, codex_root: Path) -> None:
    path = rollout(codex_root)
    with path.open("a") as handle:
        handle.write("not-json\n")
        handle.write('{"timestamp":"later","type":"event_msg","payload":{"type":"task_complete"}}\n')
    result = Indexer(config, db).scan()
    assert result["corrupt"] == 1 and result["records"] == 11


def test_truncation_reindexes_safely(config, db, codex_root: Path) -> None:
    indexer = Indexer(config, db)
    indexer.scan()
    path = rollout(codex_root)
    original = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(b"".join(original[:3]))
    result = indexer.scan()
    assert result["records"] == 3
    assert db.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 10


def test_large_session_is_processed_incrementally(config, db, codex_root: Path) -> None:
    path = rollout(codex_root)
    with path.open("a") as handle:
        for index in range(2000):
            handle.write(json.dumps({"timestamp": f"t{index}", "type": "event_msg", "payload": {"type": "agent_message", "message": "x"}}) + "\n")
    indexer = Indexer(config, db)
    assert indexer.scan()["records"] == 2010
    assert indexer.scan()["records"] == 0
