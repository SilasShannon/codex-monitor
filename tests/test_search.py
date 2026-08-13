from __future__ import annotations

from codex_monitor.indexer import Indexer
from codex_monitor.search import search


def test_search_finds_normalized_evidence(config, db) -> None:
    Indexer(config, db).scan()
    result = search(db, "new.py")
    assert result["query"] == "new.py"
    assert any(item["kind"] == "File activity" and item["title"].endswith("new.py")
               for item in result["results"])
    assert "hidden or encrypted reasoning" in result["evidence_note"]


def test_search_requires_two_characters(db) -> None:
    result = search(db, "_")
    assert result["results"] == []
    assert "at least two" in result["evidence_note"]
