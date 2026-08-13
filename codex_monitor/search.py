from __future__ import annotations

from .database import Database


def search(db: Database, query: str, limit: int = 20) -> dict:
    text = " ".join(query.split())[:200]
    if len(text) < 2:
        return {"query": text, "results": [], "truncated": False,
                "evidence_note": "Enter at least two characters to search normalized local evidence."}
    pattern = f"%{_escape(text)}%"
    results = []
    results.extend(_sessions(db, pattern, limit))
    results.extend(_text_rows(db, "assistant_messages", "Visible update", pattern, limit))
    results.extend(_text_rows(db, "prompts", "Retained prompt", pattern, limit))
    results.extend(_commands(db, pattern, limit))
    results.extend(_files(db, pattern, limit))
    results.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    truncated = len(results) > limit
    return {
        "query": text, "results": results[:limit], "truncated": truncated,
        "evidence_note": (
            "Search uses normalized local database rows only. Prompt results appear only when prompt "
            "retention was enabled; hidden or encrypted reasoning is never searched."
        ),
    }


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _sessions(db: Database, pattern: str, limit: int) -> list[dict]:
    rows = db.connection.execute(
        """SELECT s.session_id,s.last_activity timestamp,COALESCE(p.name,'Unassigned') project,
                  s.title,s.model
           FROM sessions s LEFT JOIN projects p USING(project_key)
           WHERE s.session_id LIKE ? ESCAPE '\\' OR COALESCE(s.title,'') LIKE ? ESCAPE '\\'
              OR COALESCE(s.model,'') LIKE ? ESCAPE '\\' OR COALESCE(p.name,'') LIKE ? ESCAPE '\\'
           ORDER BY COALESCE(s.last_activity,s.started_at) DESC LIMIT ?""",
        (pattern, pattern, pattern, pattern, limit),
    ).fetchall()
    return [{"kind": "Session", "session_id": row["session_id"], "timestamp": row["timestamp"],
             "project": row["project"], "title": row["title"] or row["session_id"],
             "detail": row["model"] or "Model unknown"} for row in rows]


def _text_rows(db: Database, table: str, kind: str, pattern: str, limit: int) -> list[dict]:
    rows = db.connection.execute(
        f"""SELECT x.session_id,x.timestamp,x.text,COALESCE(p.name,'Unassigned') project
            FROM {table} x JOIN sessions s USING(session_id) LEFT JOIN projects p USING(project_key)
            WHERE x.text LIKE ? ESCAPE '\\' ORDER BY x.timestamp DESC LIMIT ?""",
        (pattern, limit),
    ).fetchall()
    return [{"kind": kind, "session_id": row["session_id"], "timestamp": row["timestamp"],
             "project": row["project"], "title": _compact(row["text"]), "detail": ""} for row in rows]


def _commands(db: Database, pattern: str, limit: int) -> list[dict]:
    rows = db.connection.execute(
        """SELECT c.session_id,c.timestamp,c.name,c.arguments_json,
                  COALESCE(p.name,'Unassigned') project
           FROM tool_calls c JOIN sessions s USING(session_id) LEFT JOIN projects p USING(project_key)
           WHERE COALESCE(c.arguments_json,'') LIKE ? ESCAPE '\\'
           ORDER BY c.timestamp DESC LIMIT ?""", (pattern, limit)
    ).fetchall()
    return [{"kind": "Command / tool", "session_id": row["session_id"],
             "timestamp": row["timestamp"], "project": row["project"],
             "title": row["name"].replace("_", " "), "detail": _compact(row["arguments_json"])}
            for row in rows]


def _files(db: Database, pattern: str, limit: int) -> list[dict]:
    rows = db.connection.execute(
        """SELECT f.session_id,f.timestamp,f.path,f.action,COALESCE(p.name,'Unassigned') project
           FROM file_activity f JOIN sessions s USING(session_id) LEFT JOIN projects p USING(project_key)
           WHERE f.path LIKE ? ESCAPE '\\' ORDER BY f.timestamp DESC LIMIT ?""", (pattern, limit)
    ).fetchall()
    return [{"kind": "File activity", "session_id": row["session_id"],
             "timestamp": row["timestamp"], "project": row["project"],
             "title": row["path"], "detail": row["action"]} for row in rows]


def _compact(value: str | None, limit: int = 240) -> str:
    text = " ".join((value or "").split())
    return text if len(text) <= limit else f"{text[:limit - 1]}…"
