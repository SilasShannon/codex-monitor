from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ...database import Database
from ...sources.codex.events import safe_json
from .parser import parse_otlp_logs

MAX_REQUEST_BYTES = 10 * 1024 * 1024


def _token(attributes: dict, *names: str) -> int | None:
    for name in names:
        value = attributes.get(name)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


class _Handler(BaseHTTPRequestHandler):
    database_path: Path

    def do_POST(self) -> None:
        if self.path != "/v1/logs":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            payload = json.loads(self.rfile.read(length))
            records = parse_otlp_logs(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        db = Database(self.database_path)
        try:
            with db.transaction():
                for record in records:
                    inserted = db.connection.execute(
                        "INSERT OR IGNORE INTO telemetry_events VALUES(?,?,?,?,?,?,?,?)",
                        (record.event_id, record.timestamp, record.name, record.severity,
                         record.session_id, record.model, safe_json(record.attributes), "OTEL"),
                    )
                    kind = record.attributes.get("event.kind", record.attributes.get("kind"))
                    if record.name == "codex.sse_event" and str(kind) == "response.completed":
                        input_tokens = _token(record.attributes, "input_tokens", "input_token_count")
                        cached_tokens = _token(record.attributes, "cached_input_tokens",
                                               "cached_input_token_count", "cached_token_count")
                        cache_write_tokens = _token(record.attributes, "cache_write_input_tokens",
                                                    "cache_write_token_count")
                        output_tokens = _token(record.attributes, "output_tokens", "output_token_count")
                        reasoning_tokens = _token(record.attributes, "reasoning_output_tokens",
                                                  "reasoning_token_count")
                        db.connection.execute(
                            """INSERT OR IGNORE INTO telemetry_token_usage VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (record.event_id, record.timestamp, record.session_id, record.model,
                             input_tokens, cached_tokens, cache_write_tokens, output_tokens,
                             reasoning_tokens,
                             _token(record.attributes, "total_tokens", "total_token_count")),
                        )
                        if inserted.rowcount and record.session_id:
                            total_tokens = ((input_tokens or 0) + (output_tokens or 0))
                            db.connection.execute(
                                """INSERT INTO sessions(
                                   session_id,source_file,started_at,last_activity,model,active,
                                   input_tokens,cached_input_tokens,cache_write_input_tokens,
                                   output_tokens,reasoning_output_tokens,total_tokens,event_count)
                                   VALUES(?,?,?,?,?,1,?,?,?,?,?,?,1)
                                   ON CONFLICT(session_id) DO UPDATE SET
                                   last_activity=excluded.last_activity,
                                   model=COALESCE(excluded.model,sessions.model),active=1,
                                   input_tokens=CASE WHEN sessions.source_file LIKE 'otel:%'
                                     THEN COALESCE(sessions.input_tokens,0)+COALESCE(excluded.input_tokens,0)
                                     ELSE sessions.input_tokens END,
                                   cached_input_tokens=CASE WHEN sessions.source_file LIKE 'otel:%'
                                     THEN COALESCE(sessions.cached_input_tokens,0)+COALESCE(excluded.cached_input_tokens,0)
                                     ELSE sessions.cached_input_tokens END,
                                   cache_write_input_tokens=CASE WHEN sessions.source_file LIKE 'otel:%'
                                     THEN COALESCE(sessions.cache_write_input_tokens,0)+COALESCE(excluded.cache_write_input_tokens,0)
                                     ELSE sessions.cache_write_input_tokens END,
                                   output_tokens=CASE WHEN sessions.source_file LIKE 'otel:%'
                                     THEN COALESCE(sessions.output_tokens,0)+COALESCE(excluded.output_tokens,0)
                                     ELSE sessions.output_tokens END,
                                   reasoning_output_tokens=CASE WHEN sessions.source_file LIKE 'otel:%'
                                     THEN COALESCE(sessions.reasoning_output_tokens,0)+COALESCE(excluded.reasoning_output_tokens,0)
                                     ELSE sessions.reasoning_output_tokens END,
                                   total_tokens=CASE WHEN sessions.source_file LIKE 'otel:%'
                                     THEN COALESCE(sessions.total_tokens,0)+COALESCE(excluded.total_tokens,0)
                                     ELSE sessions.total_tokens END,
                                   event_count=sessions.event_count+1""",
                                (record.session_id, f"otel:{record.session_id}", record.timestamp,
                                 record.timestamp, record.model, input_tokens, cached_tokens,
                                 cache_write_tokens, output_tokens, reasoning_tokens, total_tokens),
                            )
        finally:
            db.close()
        body = b"{}"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class OtelReceiver:
    def __init__(self, database_path: Path, host: str = "127.0.0.1", port: int = 4318):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("OTel receiver must bind to loopback")
        _Handler.database_path = database_path
        self.server = ThreadingHTTPServer((host, port), _Handler)
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread:
            self.thread.join(timeout=5)
