from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path

from .config import Config
from .database import Database
from .models import ProjectRecord
from .projects import identify_project
from .sources.codex.discovery import discover_session_files
from .sources.codex.events import safe_json
from .sources.codex.parser import CodexEventParser, ParsedRecord

LOG = logging.getLogger(__name__)


class Indexer:
    def __init__(self, config: Config, database: Database):
        self.config = config
        self.db = database
        self._project_cache: dict[str, ProjectRecord | None] = {}

    def scan(self) -> dict[str, int]:
        result = {"files": 0, "records": 0, "corrupt": 0}
        for path in discover_session_files(self.config.data_roots):
            result["files"] += 1
            count, corrupt = self.index_file(path)
            result["records"] += count
            result["corrupt"] += corrupt
        self._mark_active()
        return result

    def index_file(self, path: Path) -> tuple[int, int]:
        stat = path.stat()
        row = self.db.connection.execute("SELECT * FROM source_files WHERE path=?", (str(path),)).fetchone()
        offset = int(row["offset"]) if row else 0
        partial = bytes(row["partial"]) if row else b""
        if stat.st_size < offset:
            offset, partial = 0, b""
        if stat.st_size == offset:
            return 0, 0
        parser = CodexEventParser(str(path))
        # Recover the session identity before parsing appended records.
        if offset:
            existing = self.db.connection.execute("SELECT session_id FROM source_files WHERE path=?", (str(path),)).fetchone()
            if existing and existing["session_id"]:
                parser.session.session_id = existing["session_id"]
                session = self.db.connection.execute("SELECT * FROM sessions WHERE session_id=?", (existing["session_id"],)).fetchone()
                if session:
                    parser.session.cwd, parser.session.model = session["cwd"], session["model"]
                    parser.session.started_at = session["started_at"]
                    parser.session.cli_version = session["cli_version"]
        with path.open("rb") as handle:
            handle.seek(offset)
            chunk = handle.read()
        new_offset = offset + len(chunk)
        data = partial + chunk
        lines = data.splitlines(keepends=True)
        trailing = b""
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            trailing = lines.pop()
        parsed_count = corrupt = 0
        with self.db.transaction():
            for line in lines:
                if not line.strip():
                    continue
                parsed = parser.parse_line(line)
                if parsed is None:
                    corrupt += 1
                    continue
                self._store(parsed)
                parsed_count += 1
            self.db.connection.execute(
                """INSERT INTO source_files(path,size,mtime_ns,offset,partial,session_id,last_error)
                   VALUES(?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET
                   size=excluded.size,mtime_ns=excluded.mtime_ns,offset=excluded.offset,
                   partial=excluded.partial,session_id=excluded.session_id,last_error=excluded.last_error""",
                (str(path), stat.st_size, stat.st_mtime_ns, new_offset, trailing,
                 parser.session.session_id or None, f"{corrupt} corrupt record(s)" if corrupt else None),
            )
        return parsed_count, corrupt

    def _store(self, item: ParsedRecord) -> None:
        session = item.session
        cwd_key = session.cwd or ""
        if cwd_key not in self._project_cache:
            self._project_cache[cwd_key] = identify_project(session.cwd, self.config.git_enabled)
        project = self._project_cache[cwd_key]
        if project:
            session.project_key = project.key
            self.db.connection.execute(
                "INSERT OR REPLACE INTO projects(project_key,name,working_directory,git_root) VALUES(?,?,?,?)",
                (project.key, project.name, project.working_directory, project.git_root),
            )
        usage = item.token_usage or session.token_usage
        self.db.connection.execute(
            """INSERT INTO sessions(session_id,source_file,started_at,ended_at,last_activity,cwd,project_key,
               model,cli_version,title,active,input_tokens,cached_input_tokens,output_tokens,
               cache_write_input_tokens,reasoning_output_tokens,total_tokens,context_window,event_count)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
               ON CONFLICT(session_id) DO UPDATE SET
               source_file=CASE WHEN sessions.source_file LIKE 'otel:%'
                 THEN excluded.source_file ELSE sessions.source_file END,
               started_at=COALESCE(sessions.started_at,excluded.started_at),
               ended_at=COALESCE(excluded.ended_at,sessions.ended_at),last_activity=excluded.last_activity,
               cwd=COALESCE(excluded.cwd,sessions.cwd),project_key=COALESCE(excluded.project_key,sessions.project_key),
               model=COALESCE(excluded.model,sessions.model),cli_version=COALESCE(excluded.cli_version,sessions.cli_version),
               input_tokens=COALESCE(excluded.input_tokens,sessions.input_tokens),
               cached_input_tokens=COALESCE(excluded.cached_input_tokens,sessions.cached_input_tokens),
               cache_write_input_tokens=COALESCE(excluded.cache_write_input_tokens,sessions.cache_write_input_tokens),
               output_tokens=COALESCE(excluded.output_tokens,sessions.output_tokens),
               reasoning_output_tokens=COALESCE(excluded.reasoning_output_tokens,sessions.reasoning_output_tokens),
               total_tokens=COALESCE(excluded.total_tokens,sessions.total_tokens),
               context_window=COALESCE(excluded.context_window,sessions.context_window)""",
            (session.session_id, session.source_file, session.started_at, session.ended_at,
             session.last_activity, session.cwd, session.project_key, session.model, session.cli_version,
             session.title, 0, usage.input_tokens, usage.cached_input_tokens, usage.output_tokens,
             usage.cache_write_input_tokens, usage.reasoning_output_tokens, usage.total_tokens,
             usage.context_window),
        )
        event = item.event
        inserted = self.db.connection.execute(
            "INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?,?,?)",
            (event.event_id, event.session_id, event.timestamp, event.category, event.subtype,
             event.turn_id, safe_json(event.data), int(event.unsupported)),
        )
        if inserted.rowcount:
            self.db.connection.execute(
                "UPDATE sessions SET event_count=event_count+1 WHERE session_id=?", (session.session_id,)
            )
        if item.prompt:
            self.db.connection.execute(
                "INSERT OR IGNORE INTO prompts VALUES(?,?,?,?)",
                (event.event_id, event.session_id, event.timestamp, item.prompt),
            )
            if not session.title:
                title = " ".join(item.prompt.split())[:100]
                self.db.connection.execute("UPDATE sessions SET title=COALESCE(title,?) WHERE session_id=?", (title, session.session_id))
        if item.tool_call:
            call = item.tool_call
            self.db.connection.execute(
                "INSERT OR IGNORE INTO tool_calls VALUES(?,?,?,?,?,?,?,?,?)",
                (call.call_id, call.session_id, call.timestamp, call.name, call.kind, call.server,
                 call.status, call.duration_ms, safe_json(call.arguments) if call.arguments else None),
            )
        if item.tool_result:
            result = item.tool_result
            self.db.connection.execute(
                "INSERT OR REPLACE INTO tool_results VALUES(?,?,?,?,?,?)",
                (result["call_id"], session.session_id, event.timestamp, int(bool(result.get("success"))),
                 result.get("duration_ms"), result.get("output", "")),
            )
        if item.token_usage:
            u = item.token_usage
            self.db.connection.execute(
                """INSERT OR IGNORE INTO token_snapshots(
                   event_id,session_id,timestamp,input_tokens,cached_input_tokens,
                   cache_write_input_tokens,output_tokens,reasoning_output_tokens,total_tokens,context_window)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (event.event_id, session.session_id, event.timestamp, u.input_tokens, u.cached_input_tokens,
                 u.cache_write_input_tokens, u.output_tokens, u.reasoning_output_tokens,
                 u.total_tokens, u.context_window),
            )
        for path, action, evidence in item.file_activity:
            self.db.connection.execute(
                "INSERT OR IGNORE INTO file_activity VALUES(?,?,?,?,?,?)",
                (event.event_id, session.session_id, event.timestamp, path, action, evidence),
            )
        if item.raw_unknown is not None:
            self.db.connection.execute(
                "INSERT OR IGNORE INTO unsupported_events VALUES(?,?,?,?,?,?)",
                (event.event_id, session.session_id, event.timestamp, event.category, event.subtype,
                 safe_json(item.raw_unknown)),
            )

    def _mark_active(self) -> None:
        cutoff = time.time() - max(self.config.scan_interval * 3, 10)
        self.db.connection.execute("UPDATE sessions SET active=0")
        for row in self.db.connection.execute("SELECT session_id,source_file,ended_at FROM sessions"):
            try:
                # Codex task_complete ends a turn, not a resumable session. Recent
                # append activity is the reliable V1 signal for session liveness.
                if str(row["source_file"]).startswith("otel:"):
                    timestamp = self.db.connection.execute(
                        "SELECT MAX(timestamp) FROM telemetry_events WHERE session_id=?",
                        (row["session_id"],),
                    ).fetchone()[0]
                    active = bool(timestamp and datetime.fromisoformat(
                        timestamp.replace("Z", "+00:00")
                    ).timestamp() >= cutoff)
                else:
                    active = Path(row["source_file"]).stat().st_mtime >= cutoff
            except OSError:
                active = False
            if active:
                self.db.connection.execute("UPDATE sessions SET active=1 WHERE session_id=?", (row["session_id"],))
        self.db.connection.commit()

    def reindex(self) -> dict[str, int]:
        self.db.close()
        self.db.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(self.db.path) + suffix).unlink(missing_ok=True)
        self.db = Database(self.db.path)
        return self.scan()
