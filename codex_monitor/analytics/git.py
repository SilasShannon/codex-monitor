from __future__ import annotations

import json
import shlex
from collections import Counter

from ..database import Database

_READ_ONLY = {"status", "log", "diff", "show", "branch", "rev-parse", "remote", "tag"}


def git_analytics(db: Database, limit: int = 50) -> dict:
    rows = db.connection.execute(
        """SELECT c.timestamp,c.arguments_json,r.success,s.session_id,
                  COALESCE(p.name,'Unassigned') project
           FROM tool_calls c LEFT JOIN tool_results r USING(call_id,session_id)
           JOIN sessions s USING(session_id) LEFT JOIN projects p USING(project_key)
           WHERE c.kind IN ('shell','tool') ORDER BY c.timestamp DESC LIMIT 500"""
    ).fetchall()
    commands = []
    operations = Counter()
    projects = set()
    sessions = set()
    failures = mutating = 0
    for row in rows:
        command = _command(row["arguments_json"])
        parsed = _git_operation(command)
        if not parsed:
            continue
        operation, safety = parsed
        operations[operation] += 1
        projects.add(row["project"])
        sessions.add(row["session_id"])
        failures += row["success"] is not None and not bool(row["success"])
        mutating += safety == "Potentially mutating"
        if len(commands) < limit:
            commands.append({
                "timestamp": row["timestamp"], "project": row["project"],
                "session_id": row["session_id"], "command": command[:300],
                "operation": operation, "safety": safety,
                "success": None if row["success"] is None else bool(row["success"]),
            })
    return {
        "summary": {"commands": sum(operations.values()), "projects": len(projects),
                    "sessions": len(sessions), "failures": failures,
                    "potentially_mutating": mutating},
        "operations": [{"name": name, "commands": count} for name, count in operations.most_common()],
        "commands": commands,
        "evidence_note": (
            "This page inspects the 500 most recent normalized shell/tool calls for Git commands. "
            "It does not run Git, "
            "inspect unobserved repository state, or claim that an unknown-outcome command succeeded."
        ),
    }


def _command(arguments_json: str | None) -> str:
    try:
        value = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return ""
    command = value.get("cmd", value.get("command", "")) if isinstance(value, dict) else ""
    return " ".join(str(part) for part in command) if isinstance(command, list) else str(command)


def _git_operation(command: str) -> tuple[str, str] | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    try:
        index = parts.index("git")
    except ValueError:
        return None
    tail = parts[index + 1:]
    while tail and tail[0].startswith("-"):
        option = tail.pop(0)
        if option in {"-C", "--git-dir", "--work-tree"} and tail:
            tail.pop(0)
    if not tail:
        return None
    operation = tail[0]
    return operation, "Read-only" if operation in _READ_ONLY else "Potentially mutating"
