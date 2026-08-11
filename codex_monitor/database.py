from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 4


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        self.connection = sqlite3.connect(path, check_same_thread=False)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection:
            yield self.connection

    def _migrate(self) -> None:
        try:
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key='schema_version'"
            ).fetchone()
            previous_version = int(row[0]) if row else 0
        except (sqlite3.OperationalError, ValueError):
            previous_version = 0
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS source_files(
              path TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
              offset INTEGER NOT NULL DEFAULT 0, partial BLOB NOT NULL DEFAULT X'',
              session_id TEXT, last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS projects(
              project_key TEXT PRIMARY KEY, name TEXT NOT NULL, working_directory TEXT NOT NULL,
              git_root TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions(
              session_id TEXT PRIMARY KEY, source_file TEXT NOT NULL, started_at TEXT, ended_at TEXT,
              last_activity TEXT, cwd TEXT, project_key TEXT, model TEXT, cli_version TEXT, title TEXT,
              active INTEGER NOT NULL DEFAULT 0, input_tokens INTEGER, cached_input_tokens INTEGER,
              cache_write_input_tokens INTEGER, output_tokens INTEGER,
              reasoning_output_tokens INTEGER, total_tokens INTEGER,
              context_window INTEGER, event_count INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY(project_key) REFERENCES projects(project_key)
            );
            CREATE TABLE IF NOT EXISTS events(
              event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT, category TEXT NOT NULL,
              subtype TEXT NOT NULL, turn_id TEXT, data_json TEXT NOT NULL, unsupported INTEGER NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS events_session_time ON events(session_id, timestamp);
            CREATE TABLE IF NOT EXISTS prompts(
              event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT, text TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS assistant_messages(
              event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT,
              text TEXT NOT NULL, phase TEXT,
              FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE INDEX IF NOT EXISTS assistant_messages_session_time
              ON assistant_messages(session_id,timestamp);
            CREATE TABLE IF NOT EXISTS tool_calls(
              call_id TEXT NOT NULL, session_id TEXT NOT NULL, timestamp TEXT, name TEXT NOT NULL,
              kind TEXT NOT NULL, server TEXT, status TEXT, duration_ms REAL, arguments_json TEXT,
              PRIMARY KEY(call_id, session_id), FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            CREATE TABLE IF NOT EXISTS tool_results(
              call_id TEXT NOT NULL, session_id TEXT NOT NULL, timestamp TEXT, success INTEGER,
              duration_ms REAL, output_preview TEXT, PRIMARY KEY(call_id, session_id)
            );
            CREATE TABLE IF NOT EXISTS file_activity(
              event_id TEXT NOT NULL, session_id TEXT NOT NULL, timestamp TEXT, path TEXT NOT NULL,
              action TEXT NOT NULL, evidence TEXT NOT NULL, PRIMARY KEY(event_id, path, action)
            );
            CREATE TABLE IF NOT EXISTS token_snapshots(
              event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT, input_tokens INTEGER,
              cached_input_tokens INTEGER, cache_write_input_tokens INTEGER, output_tokens INTEGER,
              reasoning_output_tokens INTEGER,
              total_tokens INTEGER, context_window INTEGER
            );
            CREATE TABLE IF NOT EXISTS unsupported_events(
              event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT, top_type TEXT,
              payload_type TEXT, raw_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS telemetry_events(
              event_id TEXT PRIMARY KEY, timestamp TEXT, name TEXT NOT NULL, severity TEXT,
              session_id TEXT, model TEXT, attributes_json TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'OTEL'
            );
            CREATE INDEX IF NOT EXISTS telemetry_events_session_time
              ON telemetry_events(session_id, timestamp);
            CREATE TABLE IF NOT EXISTS telemetry_token_usage(
              event_id TEXT PRIMARY KEY, timestamp TEXT, session_id TEXT, model TEXT,
              input_tokens INTEGER, cached_input_tokens INTEGER,
              cache_write_input_tokens INTEGER, output_tokens INTEGER,
              reasoning_output_tokens INTEGER, total_tokens INTEGER,
              FOREIGN KEY(event_id) REFERENCES telemetry_events(event_id)
            );
            CREATE TABLE IF NOT EXISTS telemetry_spans(
              span_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, parent_span_id TEXT,
              name TEXT NOT NULL, start_time TEXT, end_time TEXT, status TEXT,
              session_id TEXT, model TEXT, attributes_json TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'OTEL'
            );
            CREATE INDEX IF NOT EXISTS telemetry_spans_trace ON telemetry_spans(trace_id,start_time);
            CREATE TABLE IF NOT EXISTS telemetry_metrics(
              point_id TEXT PRIMARY KEY, timestamp TEXT, name TEXT NOT NULL,
              metric_type TEXT NOT NULL, value REAL, count INTEGER, sum REAL,
              session_id TEXT, model TEXT, attributes_json TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'OTEL'
            );
            CREATE INDEX IF NOT EXISTS telemetry_metrics_name_time
              ON telemetry_metrics(name,timestamp);
            """
        )
        self._ensure_column("sessions", "cache_write_input_tokens", "INTEGER")
        self._ensure_column("token_snapshots", "cache_write_input_tokens", "INTEGER")
        if previous_version and previous_version < 4:
            # Revisit historical files once so newly normalized visible assistant
            # messages can be populated without deleting any existing analytics.
            self.connection.execute("UPDATE source_files SET offset=0,partial=X''")
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)",
            (str(SCHEMA_VERSION),),
        )
        self.connection.commit()

    def _ensure_column(self, table: str, column: str, declaration: str) -> None:
        columns = {row[1] for row in self.connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
