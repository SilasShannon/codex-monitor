from __future__ import annotations

import json
from collections import Counter

from .database import Database


def _compact(value: str | None, limit: int = 240) -> str | None:
    if not value:
        return None
    text = " ".join(value.split())
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def _arguments(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def session_briefing(db: Database, session_id: str) -> dict | None:
    session = db.connection.execute(
        """SELECT s.*,p.name project_name,p.git_root,p.working_directory
           FROM sessions s LEFT JOIN projects p USING(project_key) WHERE session_id=?""",
        (session_id,),
    ).fetchone()
    if not session:
        return None
    prompts = db.connection.execute(
        "SELECT timestamp,text FROM prompts WHERE session_id=? ORDER BY timestamp DESC LIMIT 5",
        (session_id,),
    ).fetchall()
    messages = db.connection.execute(
        """SELECT timestamp,text,phase FROM assistant_messages
           WHERE session_id=? ORDER BY timestamp DESC LIMIT 8""",
        (session_id,),
    ).fetchall()
    tools = db.connection.execute(
        """SELECT c.timestamp,c.name,c.kind,c.server,c.arguments_json,r.success,r.duration_ms
           FROM tool_calls c LEFT JOIN tool_results r USING(call_id,session_id)
           WHERE c.session_id=? ORDER BY c.timestamp DESC LIMIT 100""",
        (session_id,),
    ).fetchall()
    files = db.connection.execute(
        """SELECT timestamp,path,action,evidence FROM file_activity
           WHERE session_id=? ORDER BY timestamp DESC LIMIT 100""",
        (session_id,),
    ).fetchall()

    commands = []
    test_runs = []
    for tool in tools:
        args = _arguments(tool["arguments_json"])
        command = args.get("cmd", args.get("command"))
        if isinstance(command, list):
            command = " ".join(str(part) for part in command)
        if isinstance(command, str):
            item = {"command": _compact(command, 180), "success": _success(tool["success"]),
                    "timestamp": tool["timestamp"]}
            commands.append(item)
            lowered = command.lower()
            if any(marker in lowered for marker in ("pytest", "npm test", "npm run test", "cargo test",
                                                     "go test", "pnpm test", "vitest", "jest")):
                test_runs.append(item)

    file_counts = Counter(row["action"] for row in files)
    tool_counts = Counter(_tool_label(row) for row in tools)
    concepts = _concepts(commands, files, tools)
    request = _compact(prompts[0]["text"], 400) if prompts else None
    latest_update = _compact(messages[0]["text"], 600) if messages else None
    observations = []
    if tools:
        observations.append(f"Observed {len(tools)} tool calls: " + ", ".join(
            f"{name} ({count})" for name, count in tool_counts.most_common(5)
        ) + ".")
    if files:
        observations.append("Observed file work: " + ", ".join(
            f"{count} {action}" for action, count in sorted(file_counts.items())
        ) + ".")
    if test_runs:
        passed = sum(item["success"] is True for item in test_runs)
        failed = sum(item["success"] is False for item in test_runs)
        observations.append(f"Observed {len(test_runs)} test command(s): {passed} succeeded, {failed} failed, "
                            f"and {len(test_runs) - passed - failed} have no reliable result.")
    if not observations:
        observations.append("No tool, file, or test activity has been reliably observed yet.")

    return {
        "session_id": session_id,
        "project": session["project_name"] or "Unassigned",
        "path": session["git_root"] or session["working_directory"] or session["cwd"],
        "title": session["title"],
        "model": session["model"],
        "active": bool(session["active"]),
        "last_activity": session["last_activity"],
        "request": request,
        "plain_language_status": _status(bool(session["active"]), request, latest_update),
        "latest_visible_update": latest_update,
        "observations": observations,
        "commands": commands[:12],
        "tests": test_runs[:8],
        "files": [dict(row) for row in files[:20]],
        "concepts": concepts,
        "visible_updates": [
            {"timestamp": row["timestamp"], "phase": row["phase"], "text": _compact(row["text"], 600)}
            for row in messages
        ],
        "evidence_note": (
            "This briefing uses visible Codex messages and observed tools/files only. "
            "It does not expose or reconstruct hidden reasoning."
        ),
    }


def active_briefings(db: Database) -> list[dict]:
    ids = [row[0] for row in db.connection.execute(
        "SELECT session_id FROM sessions WHERE active=1 ORDER BY last_activity DESC"
    )]
    return [briefing for session_id in ids if (briefing := session_briefing(db, session_id))]


def _success(value: object) -> bool | None:
    return None if value is None else bool(value)


def _tool_label(row) -> str:
    if row["kind"] == "mcp":
        return f"MCP {row['server'] or 'tool'}"
    if row["name"] in {"exec_command", "shell"}:
        return "shell commands"
    return str(row["name"]).replace("_", " ")


def _status(active: bool, request: str | None, latest: str | None) -> str:
    state = "This session has recent activity" if active else "This session is not currently active"
    if request and latest:
        return f"{state}. The request is “{request}”. The latest visible Codex update says: “{latest}”"
    if request:
        return f"{state}. The request is “{request}”."
    if latest:
        return f"{state}. The latest visible Codex update says: “{latest}”"
    return f"{state}, but there is not enough visible evidence to describe its progress yet."


def _concepts(commands, files, tools) -> list[dict[str, str]]:
    evidence = " ".join(
        [str(item.get("command") or "") for item in commands]
        + [str(row["path"]) for row in files]
        + [str(row["name"]) for row in tools]
    ).lower()
    candidates = [
        (("pytest", "test", "jest", "vitest"), "Automated testing",
         "Tests turn expected behavior into repeatable checks and help prevent regressions."),
        (("migration", "sqlite", "database", ".sql"), "Database migrations",
         "Migrations evolve stored data deliberately while preserving existing installations."),
        (("api", "server", "endpoint", "route"), "API boundaries",
         "An API separates data and business logic from the interface that presents it."),
        ((".tsx", ".jsx", "react", "frontend"), "Component-based frontend design",
         "Components divide a user interface into reusable pieces with explicit data inputs."),
        (("otel", "telemetry", "trace", "metric"), "Observability signals",
         "Logs describe events, metrics summarize measurements, and traces connect timed operations."),
        (("cache",), "Caching",
         "Caching reuses prior work to reduce latency or cost, but requires clear freshness rules."),
    ]
    return [
        {"name": name, "explanation": explanation}
        for markers, name, explanation in candidates if any(marker in evidence for marker in markers)
    ][:5]
