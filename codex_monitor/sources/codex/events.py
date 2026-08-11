from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_event_id(session_id: str, record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{session_id}\0{canonical}".encode()).hexdigest()


def payload_type(record: dict[str, Any]) -> str:
    payload = record.get("payload")
    return str(payload.get("type", "")) if isinstance(payload, dict) else ""


def safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
