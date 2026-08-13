from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal

from .analytics.costs import _timestamp, _usage
from .database import Database
from .pricing import estimate_cost


def project_overviews(db: Database, limit: int = 50) -> list[dict]:
    projects = db.connection.execute(
        """SELECT p.*,COUNT(s.session_id) sessions,COALESCE(SUM(s.active),0) active_sessions,
                  MAX(COALESCE(s.last_activity,s.started_at)) last_activity,
                  COALESCE(SUM(s.total_tokens),0) total_tokens,
                  COALESCE(SUM(s.input_tokens),0) input_tokens,
                  COALESCE(SUM(s.cached_input_tokens),0) cached_input_tokens
           FROM projects p LEFT JOIN sessions s USING(project_key)
           GROUP BY p.project_key ORDER BY last_activity DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [_project(db, row) for row in projects]


def _project(db: Database, project) -> dict:
    key = project["project_key"]
    sessions = db.connection.execute(
        "SELECT * FROM sessions WHERE project_key=? ORDER BY COALESCE(last_activity,started_at) DESC",
        (key,),
    ).fetchall()
    tools = db.connection.execute(
        """SELECT c.name,c.kind,c.server,c.arguments_json,r.success
           FROM tool_calls c LEFT JOIN tool_results r USING(call_id,session_id)
           JOIN sessions s USING(session_id) WHERE s.project_key=?""",
        (key,),
    ).fetchall()
    files = db.connection.execute(
        """SELECT f.path,f.action FROM file_activity f JOIN sessions s USING(session_id)
           WHERE s.project_key=?""",
        (key,),
    ).fetchall()
    costs = Decimal(0)
    priced = unpriced = 0
    models = Counter()
    for session in sessions:
        models[session["model"] or "Unknown"] += 1
        estimate = estimate_cost(
            session["model"], _usage(session), at=_timestamp(session["started_at"])
        )
        if estimate.estimated_api_equivalent_cost is None:
            unpriced += 1
        else:
            priced += 1
            costs += estimate.estimated_api_equivalent_cost
    test_calls = sum(_is_test(row["arguments_json"]) for row in tools)
    failures = sum(row["success"] is not None and not bool(row["success"]) for row in tools)
    file_actions = Counter(row["action"] for row in files)
    tool_kinds = Counter("MCP" if row["kind"] == "mcp" else row["name"] for row in tools)
    highlights = _highlights(len(sessions), tools, files, test_calls, failures)
    # Cached input is included in input_tokens, so adding it again understates the rate.
    denominator = project["input_tokens"] or 0
    return {
        "project_key": key,
        "name": project["name"],
        "path": project["git_root"] or project["working_directory"],
        "sessions": project["sessions"],
        "active_sessions": project["active_sessions"],
        "last_activity": project["last_activity"],
        "total_tokens": project["total_tokens"],
        "cache_rate": project["cached_input_tokens"] / denominator if denominator else None,
        "estimated_api_equivalent_cost": str(costs),
        "priced_sessions": priced,
        "unpriced_sessions": unpriced,
        "tool_calls": len(tools),
        "test_commands": test_calls,
        "failed_tools": failures,
        "files_touched": len({row["path"] for row in files}),
        "file_actions": dict(file_actions),
        "top_tools": [{"name": name, "calls": count} for name, count in tool_kinds.most_common(5)],
        "models": [{"name": name, "sessions": count} for name, count in models.most_common()],
        "highlights": highlights,
        "evidence_note": (
            "This summary describes normalized local activity, not unobserved project goals, "
            "code quality, or private model reasoning."
        ),
    }


def _is_test(arguments_json: str | None) -> bool:
    try:
        value = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return False
    command = value.get("cmd", value.get("command", "")) if isinstance(value, dict) else ""
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    lowered = str(command).lower()
    return any(marker in lowered for marker in (
        "pytest", "npm test", "npm run test", "vitest", "jest", "cargo test", "go test"
    ))


def _highlights(session_count: int, tools, files, tests: int, failures: int) -> list[str]:
    result = [f"Codex Monitor observed {session_count} session(s) associated with this project."]
    if files:
        result.append(
            f"Observed implementation activity touched {len({row['path'] for row in files})} distinct file(s)."
        )
    if tests:
        result.append(f"Observed {tests} test command(s), providing evidence of verification work.")
    if tools:
        result.append(f"Observed {len(tools)} tool call(s) supporting investigation or implementation.")
    if failures:
        result.append(f"Observed {failures} explicit tool failure(s) that may warrant review.")
    return result
