from __future__ import annotations

from codex_monitor.indexer import Indexer
from codex_monitor.live import render
from codex_monitor.queries import overview, projects, session_detail, sessions


def test_queries_and_search(config, db) -> None:
    Indexer(config, db).scan()
    assert overview(db)["sessions"] == 1
    assert projects(db)[0]["name"] == "example-project"
    assert sessions(db, search="safe parser")[0]["session_id"] == "session-test-1"
    detail = session_detail(db, "session-test-1")
    assert detail and detail["prompts"][0]["text"] == "Build a safe parser"
    assert len(detail["tools"]) == 2


def test_live_never_fabricates_activity(config, db) -> None:
    Indexer(config, db).scan()
    output = render(db)
    assert "current activity" not in output.lower()
    assert "No reliably active" in output
