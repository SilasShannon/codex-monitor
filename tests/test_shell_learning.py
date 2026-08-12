from __future__ import annotations

from codex_monitor.indexer import Indexer
from codex_monitor.shell_learning import explain_command, shell_lessons


def test_explains_command_without_claiming_intent() -> None:
    lesson = explain_command("git status --short")
    assert lesson["category"] == "Version control"
    assert lesson["safety"] == "Read-only"
    assert lesson["parts"][1]["syntax"] == "status"
    assert "inspect" in lesson["purpose"]


def test_redacts_sensitive_assignments() -> None:
    lesson = explain_command("API_TOKEN=super-secret curl https://example.test")
    assert "super-secret" not in lesson["command"]
    assert "API_TOKEN=<redacted>" in lesson["command"]
    assert lesson["executable"] == "curl"
    assert lesson["category"] == "Networking"


def test_explains_the_program_inside_a_shell_wrapper() -> None:
    lesson = explain_command("bash -lc 'cd /tmp/project && pytest -q'")
    assert lesson["executable"] == "pytest"
    assert lesson["category"] == "Testing"
    assert lesson["parts"][0]["syntax"] == "bash -c"


def test_destructive_commands_are_labeled_clearly() -> None:
    lesson = explain_command("rm generated.tmp")
    assert lesson["category"] == "File management"
    assert lesson["safety"].startswith("Destructive")


def test_shell_lessons_use_normalized_observations(config, db) -> None:
    Indexer(config, db).scan()
    result = shell_lessons(db)
    assert result["summary"]["commands"] == 1
    assert result["lessons"][0]["command"] == "pytest"
    assert result["lessons"][0]["success"] is True
    assert "private intent" in result["evidence_note"]
