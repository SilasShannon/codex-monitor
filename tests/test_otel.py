from __future__ import annotations

from codex_monitor.sources.otel import parse_otlp_logs


def test_parse_otlp_json_log() -> None:
    payload = {"resourceLogs": [{
        "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "codex_cli_rs"}}]},
        "scopeLogs": [{"logRecords": [{
            "timeUnixNano": "1704067200000000000",
            "body": {"stringValue": "codex.sse_event"},
            "attributes": [
                {"key": "conversation.id", "value": {"stringValue": "session-1"}},
                {"key": "model", "value": {"stringValue": "gpt-5.6-sol"}},
                {"key": "event.kind", "value": {"stringValue": "response.completed"}},
                {"key": "input_tokens", "value": {"intValue": "123"}},
                {"key": "user.email", "value": {"stringValue": "private@example.com"}},
            ],
        }]}],
    }]}
    records = parse_otlp_logs(payload)
    assert len(records) == 1
    assert records[0].name == "codex.sse_event"
    assert records[0].session_id == "session-1"
    assert records[0].attributes["input_tokens"] == 123
    assert "user.email" not in records[0].attributes
