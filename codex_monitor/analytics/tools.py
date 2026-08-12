from __future__ import annotations

from ..database import Database


def tool_analytics(db: Database, *, mcp_only: bool = False, limit: int = 50) -> dict:
    """Aggregate observed calls without inferring missing outcomes or durations."""
    comparison = "=" if mcp_only else "!="
    rows = db.connection.execute(
        f"""SELECT c.name,c.server,c.kind,COUNT(*) calls,
            SUM(CASE WHEN r.success=1 THEN 1 ELSE 0 END) successes,
            SUM(CASE WHEN r.success=0 THEN 1 ELSE 0 END) failures,
            SUM(CASE WHEN r.success IS NULL THEN 1 ELSE 0 END) unknown_outcomes,
            AVG(COALESCE(r.duration_ms,c.duration_ms)) average_duration_ms,
            COUNT(DISTINCT c.session_id) sessions,
            COUNT(DISTINCT s.project_key) projects,
            MAX(c.timestamp) last_activity
           FROM tool_calls c
           LEFT JOIN tool_results r USING(call_id,session_id)
           LEFT JOIN sessions s USING(session_id)
           WHERE c.kind {comparison} ?
           GROUP BY c.name,c.server,c.kind
           ORDER BY calls DESC,last_activity DESC LIMIT ?""",
        ("mcp", limit),
    ).fetchall()
    summary = db.connection.execute(
        f"""SELECT COUNT(*) calls,
            SUM(CASE WHEN r.success=1 THEN 1 ELSE 0 END) successes,
            SUM(CASE WHEN r.success=0 THEN 1 ELSE 0 END) failures,
            SUM(CASE WHEN r.success IS NULL THEN 1 ELSE 0 END) unknown_outcomes,
            AVG(COALESCE(r.duration_ms,c.duration_ms)) average_duration_ms,
            COUNT(DISTINCT c.session_id) sessions,
            COUNT(DISTINCT s.project_key) projects
           FROM tool_calls c
           LEFT JOIN tool_results r USING(call_id,session_id)
           LEFT JOIN sessions s USING(session_id)
           WHERE c.kind {comparison} ?""",
        ("mcp",),
    ).fetchone()
    summary_values = dict(summary)
    return {
        "scope": "mcp" if mcp_only else "tools",
        "summary": {key: (value or 0) for key, value in summary_values.items()},
        "rows": [dict(row) for row in rows],
        "evidence_note": (
            "Outcomes and durations remain unknown when Codex did not expose them. "
            "Calls are grouped only from normalized local events."
        ),
    }
