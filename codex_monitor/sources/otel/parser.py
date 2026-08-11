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
                attributes = {**resource, **_attributes(record.get("attributes", []))}
                attributes = {key: value for key, value in attributes.items() if key not in SENSITIVE_KEYS}
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


def _first(attributes: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = attributes.get(key)
        if value is not None:
            return str(value)
    return None
