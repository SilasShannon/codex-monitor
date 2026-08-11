from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1


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
              output_tokens INTEGER, reasoning_output_tokens INTEGER, total_tokens INTEGER,
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
              cached_input_tokens INTEGER, output_tokens INTEGER, reasoning_output_tokens INTEGER,
              total_tokens INTEGER, context_window INTEGER
            );
            CREATE TABLE IF NOT EXISTS unsupported_events(
              event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, timestamp TEXT, top_type TEXT,
              payload_type TEXT, raw_json TEXT NOT NULL
            );
            """
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)",
            (str(SCHEMA_VERSION),),
        )
        self.connection.commit()
