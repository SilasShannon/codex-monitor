from __future__ import annotations

import errno

import pytest

from codex_monitor.config import Config
from codex_monitor.web import server


def test_dashboard_port_conflict_has_actionable_message(monkeypatch) -> None:
    def occupied(*args, **kwargs):
        raise OSError(errno.EADDRINUSE, "Address already in use")

    monkeypatch.setattr(server, "ThreadingHTTPServer", occupied)
    with pytest.raises(server.ServerStartupError) as caught:
        server._http_server("127.0.0.1", 8787, object, "Dashboard")
    message = str(caught.value)
    assert "127.0.0.1:8787" in message
    assert "already be running" in message


def test_non_port_bind_errors_are_not_hidden(monkeypatch) -> None:
    def denied(*args, **kwargs):
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(server, "ThreadingHTTPServer", denied)
    with pytest.raises(OSError, match="Permission denied"):
        server._http_server("127.0.0.1", 80, object, "Dashboard")


def test_otel_conflict_closes_dashboard_socket(monkeypatch, db) -> None:
    class Dashboard:
        closed = False

        def server_close(self):
            self.closed = True

    dashboard = Dashboard()

    class OccupiedReceiver:
        def __init__(self, *args, **kwargs):
            raise OSError(errno.EADDRINUSE, "Address already in use")

    monkeypatch.setattr(server, "_http_server", lambda *args: dashboard)
    monkeypatch.setattr(server, "OtelReceiver", OccupiedReceiver)
    monkeypatch.setattr(server.Indexer, "scan", lambda self: {})
    config = Config(database=db.path, data_roots=(), otel_enabled=True)
    with pytest.raises(server.ServerStartupError, match="Telemetry receiver port"):
        server.serve(config, db, "127.0.0.1", 8787)
    assert dashboard.closed
