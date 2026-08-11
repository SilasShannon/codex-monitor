from __future__ import annotations

from .database import Database


def sessions(db: Database, limit: int = 100, search: str | None = None) -> list[dict]:
    params: list[object] = []
    where = ""
    if search:
        where = "WHERE s.session_id LIKE ? OR s.cwd LIKE ? OR s.title LIKE ? OR p.name LIKE ?"
        value = f"%{search}%"
        params.extend([value] * 4)
    params.append(limit)
    rows = db.connection.execute(
        f"""SELECT s.*,p.name project_name FROM sessions s LEFT JOIN projects p USING(project_key)
        {where} ORDER BY COALESCE(s.last_activity,s.started_at) DESC LIMIT ?""", params
    ).fetchall()
    return [dict(row) for row in rows]


def projects(db: Database) -> list[dict]:
    rows = db.connection.execute(
        """SELECT p.*,COUNT(s.session_id) session_count,MAX(s.last_activity) last_activity,
        COALESCE(SUM(s.total_tokens),0) total_tokens FROM projects p
        LEFT JOIN sessions s USING(project_key) GROUP BY p.project_key ORDER BY last_activity DESC"""
    ).fetchall()
    return [dict(row) for row in rows]


def session_detail(db: Database, session_id: str) -> dict | None:
    row = db.connection.execute(
        "SELECT s.*,p.name project_name,p.git_root FROM sessions s LEFT JOIN projects p USING(project_key) WHERE session_id=?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["prompts"] = [dict(item) for item in db.connection.execute(
        "SELECT timestamp,text FROM prompts WHERE session_id=? ORDER BY timestamp", (session_id,)
    )]
    result["tools"] = [dict(item) for item in db.connection.execute(
        """SELECT c.*,r.success,r.duration_ms result_duration_ms FROM tool_calls c
        LEFT JOIN tool_results r USING(call_id,session_id) WHERE c.session_id=? ORDER BY c.timestamp""", (session_id,)
    )]
    result["events"] = [dict(item) for item in db.connection.execute(
        "SELECT timestamp,category,subtype,data_json,unsupported FROM events WHERE session_id=? ORDER BY timestamp", (session_id,)
    )]
    return result


def overview(db: Database) -> dict:
    totals = db.connection.execute(
        """SELECT COUNT(*) sessions,COALESCE(SUM(active),0) active_sessions,
        COALESCE(SUM(total_tokens),0) total_tokens,
        COALESCE(SUM(input_tokens),0) input_tokens,
        COALESCE(SUM(cached_input_tokens),0) cached_input_tokens,
        COALESCE(SUM(cache_write_input_tokens),0) cache_write_input_tokens,
        COALESCE(SUM(output_tokens),0) output_tokens FROM sessions"""
    ).fetchone()
    tools = db.connection.execute("SELECT COUNT(*) count FROM tool_calls").fetchone()[0]
    mcp = db.connection.execute("SELECT COUNT(*) count FROM tool_calls WHERE kind='mcp'").fetchone()[0]
    unsupported = db.connection.execute("SELECT COUNT(*) count FROM unsupported_events").fetchone()[0]
    result = dict(totals)
    denominator = result["input_tokens"] + result["cached_input_tokens"]
    result["cache_rate"] = result["cached_input_tokens"] / denominator if denominator else None
    return {**result, "tool_calls": tools, "mcp_calls": mcp, "unsupported_events": unsupported}
