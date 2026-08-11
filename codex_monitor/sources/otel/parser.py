from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

SENSITIVE_KEYS = {"user.email", "user.account_id", "user_prompt", "prompt", "content"}


@dataclass(frozen=True)
class OtelLogRecord:
    event_id: str
    timestamp: str | None
    name: str
    severity: str | None
    session_id: str | None
    model: str | None
    attributes: dict[str, Any]


@dataclass(frozen=True)
class OtelSpan:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    start_time: str | None
    end_time: str | None
    status: str | None
    session_id: str | None
    model: str | None
    attributes: dict[str, Any]


@dataclass(frozen=True)
class OtelMetricPoint:
    point_id: str
    timestamp: str | None
    name: str
    metric_type: str
    value: float | None
    count: int | None
    sum: float | None
    session_id: str | None
    model: str | None
    attributes: dict[str, Any]


def _value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "intValue", "doubleValue", "boolValue", "bytesValue"):
        if key in value:
            raw = value[key]
            return int(raw) if key == "intValue" else raw
    if "arrayValue" in value:
        return [_value(item) for item in value["arrayValue"].get("values", [])]
    if "kvlistValue" in value:
        return _attributes(value["kvlistValue"].get("values", []))
    return value


def _attributes(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {str(item.get("key")): _value(item.get("value")) for item in items if item.get("key")}


def _timestamp(nanos: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(nanos) / 1_000_000_000, timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def parse_otlp_logs(payload: dict[str, Any]) -> list[OtelLogRecord]:
    parsed: list[OtelLogRecord] = []
    for resource_log in payload.get("resourceLogs", []):
        resource = _attributes(resource_log.get("resource", {}).get("attributes", []))
        for scope_log in resource_log.get("scopeLogs", []):
            for record in scope_log.get("logRecords", []):
                attributes = _sanitize({**resource, **_attributes(record.get("attributes", []))})
                body = _value(record.get("body"))
                name = str(attributes.get("event.name") or attributes.get("name") or body or "unknown")
                timestamp = _timestamp(record.get("timeUnixNano") or record.get("observedTimeUnixNano"))
                identity = json.dumps([timestamp, name, attributes, record.get("traceId"), record.get("spanId")],
                                      sort_keys=True, default=str).encode()
                parsed.append(OtelLogRecord(
                    hashlib.sha256(identity).hexdigest(), timestamp, name,
                    record.get("severityText"),
                    _first(attributes, "conversation.id", "conversation_id", "session.id", "session_id"),
                    _first(attributes, "model", "gen_ai.request.model"), attributes,
                ))
    return parsed


def parse_otlp_traces(payload: dict[str, Any]) -> list[OtelSpan]:
    parsed: list[OtelSpan] = []
    for resource_spans in payload.get("resourceSpans", []):
        resource = _attributes(resource_spans.get("resource", {}).get("attributes", []))
        for scope_spans in resource_spans.get("scopeSpans", []):
            for span in scope_spans.get("spans", []):
                attributes = _sanitize({**resource, **_attributes(span.get("attributes", []))})
                status = span.get("status", {}).get("code")
                parsed.append(OtelSpan(
                    str(span.get("spanId", "")), str(span.get("traceId", "")),
                    str(span.get("parentSpanId")) if span.get("parentSpanId") else None,
                    str(span.get("name", "unknown")), _timestamp(span.get("startTimeUnixNano")),
                    _timestamp(span.get("endTimeUnixNano")), str(status) if status is not None else None,
                    _first(attributes, "conversation.id", "conversation_id", "session.id", "session_id"),
                    _first(attributes, "model", "gen_ai.request.model"), attributes,
                ))
    return [span for span in parsed if span.span_id and span.trace_id]


def parse_otlp_metrics(payload: dict[str, Any]) -> list[OtelMetricPoint]:
    parsed: list[OtelMetricPoint] = []
    for resource_metrics in payload.get("resourceMetrics", []):
        resource = _attributes(resource_metrics.get("resource", {}).get("attributes", []))
        for scope_metrics in resource_metrics.get("scopeMetrics", []):
            for metric in scope_metrics.get("metrics", []):
                name = str(metric.get("name", "unknown"))
                for metric_type in ("gauge", "sum", "histogram"):
                    if metric_type not in metric:
                        continue
                    for point in metric[metric_type].get("dataPoints", []):
                        attributes = _sanitize({**resource, **_attributes(point.get("attributes", []))})
                        timestamp = _timestamp(point.get("timeUnixNano"))
                        value = point.get("asDouble", point.get("asInt"))
                        identity = json.dumps([name, metric_type, timestamp, attributes, value,
                                               point.get("count"), point.get("sum")],
                                              sort_keys=True, default=str).encode()
                        parsed.append(OtelMetricPoint(
                            hashlib.sha256(identity).hexdigest(), timestamp, name, metric_type,
                            float(value) if value is not None else None,
                            int(point["count"]) if point.get("count") is not None else None,
                            float(point["sum"]) if point.get("sum") is not None else None,
                            _first(attributes, "conversation.id", "conversation_id", "session.id", "session_id"),
                            _first(attributes, "model", "gen_ai.request.model"), attributes,
                        ))
    return parsed


def _first(attributes: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = attributes.get(key)
        if value is not None:
            return str(value)
    return None


def _sanitize(attributes: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in attributes.items() if key not in SENSITIVE_KEYS}
