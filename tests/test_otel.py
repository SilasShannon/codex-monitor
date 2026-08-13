from __future__ import annotations

import pytest

from codex_monitor.sources.otel import parse_otlp_logs, parse_otlp_metrics, parse_otlp_traces
from codex_monitor.sources.otel.receiver import _decode_payload


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


def test_parse_otlp_trace() -> None:
    payload = {"resourceSpans": [{"scopeSpans": [{"spans": [{
        "traceId": "trace-1", "spanId": "span-1", "name": "codex.turn",
        "startTimeUnixNano": "1704067200000000000",
        "endTimeUnixNano": "1704067201000000000",
        "attributes": [
            {"key": "conversation.id", "value": {"stringValue": "session-1"}},
            {"key": "user.account_id", "value": {"stringValue": "private"}},
        ],
        "status": {"code": 1},
    }]}]}]}
    spans = parse_otlp_traces(payload)
    assert spans[0].trace_id == "trace-1"
    assert spans[0].session_id == "session-1"
    assert "user.account_id" not in spans[0].attributes


def test_parse_otlp_metric_points() -> None:
    payload = {"resourceMetrics": [{"scopeMetrics": [{"metrics": [{
        "name": "codex.api_request.duration_ms",
        "histogram": {"dataPoints": [{
            "timeUnixNano": "1704067201000000000", "count": "2", "sum": 42.5,
            "attributes": [{"key": "model", "value": {"stringValue": "gpt-5.6-sol"}}],
        }]},
    }, {
        "name": "codex.api_request",
        "sum": {"dataPoints": [{"timeUnixNano": "1704067201000000000", "asInt": "3"}]},
    }]}]}]}
    points = parse_otlp_metrics(payload)
    assert points[0].name == "codex.api_request.duration_ms"
    assert points[0].count == 2
    assert points[0].sum == 42.5
    assert points[0].model == "gpt-5.6-sol"
    assert points[1].value == 3


def test_decode_otlp_protobuf_log() -> None:
    from google.protobuf.json_format import ParseDict
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest

    message = ParseDict({"resourceLogs": [{"scopeLogs": [{"logRecords": [{
        "timeUnixNano": "1704067200000000000",
        "body": {"stringValue": "codex.sse_event"},
        "attributes": [{
            "key": "conversation.id", "value": {"stringValue": "protobuf-session"},
        }],
    }]}]}]}, ExportLogsServiceRequest())

    payload, response, content_type = _decode_payload(
        "/v1/logs", "application/x-protobuf", message.SerializeToString()
    )
    records = parse_otlp_logs(payload)

    assert records[0].name == "codex.sse_event"
    assert records[0].session_id == "protobuf-session"
    assert response == b""
    assert content_type == "application/x-protobuf"


def test_decode_otlp_json_with_content_type_parameter() -> None:
    payload, response, content_type = _decode_payload(
        "/v1/logs", "application/json; charset=utf-8", b'{"resourceLogs": []}'
    )
    assert payload == {"resourceLogs": []}
    assert response == b"{}"
    assert content_type == "application/json"


def test_reject_invalid_otlp_protobuf() -> None:
    with pytest.raises(ValueError, match="invalid OTLP protobuf payload"):
        _decode_payload("/v1/traces", "application/x-protobuf", b"not protobuf")


def test_reject_unsupported_otlp_media_type() -> None:
    with pytest.raises(LookupError):
        _decode_payload("/v1/metrics", "text/plain", b"{}")
