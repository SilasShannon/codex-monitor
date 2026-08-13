from __future__ import annotations

import json

from codex_monitor.analytics.git import _git_operation, git_analytics


def test_git_analytics_uses_normalized_commands(db) -> None:
    db.connection.execute("INSERT INTO projects VALUES(?,?,?,?)", ("git-key", "git-app", "/tmp/git-app", "/tmp/git-app"))
    db.connection.execute(
        "INSERT INTO sessions(session_id,source_file,project_key,active,event_count) VALUES(?,?,?,?,?)",
        ("git-session", "synthetic", "git-key", 0, 0),
    )
    for call_id, command, success in [("one", "git status --short", 1), ("two", "git commit -m test", 0)]:
        db.connection.execute(
            "INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?,?,?)",
            (call_id, "git-session", "2026-08-13T12:00:00Z", "exec_command", "shell",
             None, None, None, json.dumps({"cmd": command})),
        )
        db.connection.execute(
            "INSERT INTO tool_results VALUES(?,?,?,?,?,?)",
            (call_id, "git-session", "2026-08-13T12:00:01Z", success, None, None),
        )
    result = git_analytics(db)
    assert result["summary"] == {"commands": 2, "projects": 1, "sessions": 1,
                                  "failures": 1, "potentially_mutating": 1}
    assert result["commands"][0]["project"] == "git-app"
    assert {item["safety"] for item in result["commands"]} == {"Read-only", "Potentially mutating"}


def test_git_operation_handles_working_directory_option() -> None:
    assert _git_operation("git -C /tmp/example diff --stat") == ("diff", "Read-only")
    assert _git_operation("pytest") is None
