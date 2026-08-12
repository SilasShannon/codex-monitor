from __future__ import annotations

from codex_monitor.indexer import Indexer
from codex_monitor.project_overviews import project_overviews


def test_project_overview_uses_observed_evidence(config, db) -> None:
    Indexer(config, db).scan()
    result = project_overviews(db)
    assert len(result) == 1
    project = result[0]
    assert project["name"] == "example-project"
    assert project["sessions"] == 1
    assert project["tool_calls"] == 2
    assert project["test_commands"] == 1
    assert project["files_touched"] == 1
    assert project["unpriced_sessions"] == 1
    assert any("verification work" in item for item in project["highlights"])
    assert "not unobserved project goals" in project["evidence_note"]


def test_project_overview_is_empty_without_projects(db) -> None:
    assert project_overviews(db) == []
