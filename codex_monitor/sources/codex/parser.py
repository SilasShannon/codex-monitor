from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ...models import NormalizedEvent, SessionRecord, TokenUsage, ToolCall
from .events import payload_type, stable_event_id
from .versions import SUPPORTED_TOP_LEVEL

LOG = logging.getLogger(__name__)


@dataclass
class ParsedRecord:
    event: NormalizedEvent
    session: SessionRecord
    prompt: str | None = None
    tool_call: ToolCall | None = None
    tool_result: dict[str, Any] | None = None
    token_usage: TokenUsage | None = None
    file_activity: list[tuple[str, str, str]] = field(default_factory=list)
    raw_unknown: dict[str, Any] | None = None


def _text_content(payload: dict[str, Any]) -> str | None:
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in {"input_text", "text"}:
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts) or None
    message = payload.get("message")
    return message if isinstance(message, str) else None


def _arguments(payload: dict[str, Any]) -> dict[str, Any] | None:
    value = payload.get("arguments", payload.get("input"))
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"raw": value[:4096]}
    return None


def _mcp_parts(name: str, namespace: str | None) -> tuple[str | None, str]:
    combined = namespace or name
    if combined.startswith("mcp__"):
        parts = combined.split("__", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return None, name


def _duration_ms(value: Any, *, seconds: bool = False) -> float | None:
    if isinstance(value, (int, float)):
        return float(value) * 1000 if seconds else float(value)
    if isinstance(value, dict):
        seconds_value = value.get("secs", value.get("seconds", 0))
        nanos = value.get("nanos", value.get("nanoseconds", 0))
        if isinstance(seconds_value, (int, float)) and isinstance(nanos, (int, float)):
            return float(seconds_value) * 1000 + float(nanos) / 1_000_000
    return None


class CodexEventParser:
    """Version-tolerant adapter from Codex rollout records to stable records."""

    def __init__(self, source_file: str):
        self.source_file = source_file
        self.session = SessionRecord(session_id="", source_file=source_file)

    def parse_line(self, line: bytes) -> ParsedRecord | None:
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            LOG.warning("Skipping corrupt Codex JSONL record in %s: %s", self.source_file, exc)
            return None
        if not isinstance(record, dict):
            return None
        top = str(record.get("type", "unknown"))
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        subtype = payload_type(record) or top
        timestamp = record.get("timestamp")

        if top == "session_meta":
            self._apply_meta(payload)
        if not self.session.session_id:
            # Rollouts should start with session_meta; malformed files remain isolated.
            self.session.session_id = f"orphan:{self.source_file}"
        if timestamp:
            self.session.last_activity = str(timestamp)
            self.session.started_at = self.session.started_at or str(timestamp)

        event_id = stable_event_id(self.session.session_id, record)
        event = NormalizedEvent(
            event_id, self.session.session_id, str(timestamp) if timestamp else None,
            top, subtype, str(payload.get("turn_id")) if payload.get("turn_id") else None,
        )
        parsed = ParsedRecord(event=event, session=self.session)

        if top not in SUPPORTED_TOP_LEVEL:
            return self._unsupported(parsed, record)
        if top == "session_meta":
            event.data = {"source": payload.get("source"), "originator": payload.get("originator")}
        elif top == "turn_context":
            self.session.model = payload.get("model") or self.session.model
            self.session.cwd = payload.get("cwd") or self.session.cwd
            if payload.get("comp_hash") and payload.get("summary"):
                event.subtype = "compaction"
            event.data = {"model": payload.get("model"), "cwd": payload.get("cwd")}
        elif top == "world_state":
            event.data = {"full": bool(payload.get("full"))}
        elif top == "response_item":
            self._parse_response_item(parsed, payload, record)
        elif top == "event_msg":
            self._parse_event_msg(parsed, payload, record)
        return parsed

    def _apply_meta(self, payload: dict[str, Any]) -> None:
        session_id = payload.get("id") or payload.get("session_id")
        if session_id:
            self.session.session_id = str(session_id)
        self.session.cwd = payload.get("cwd") or self.session.cwd
        self.session.cli_version = payload.get("cli_version") or self.session.cli_version
        self.session.started_at = payload.get("timestamp") or self.session.started_at
        context = payload.get("context_window")
        if isinstance(context, int):
            self.session.token_usage.context_window = context

    def _parse_response_item(self, out: ParsedRecord, payload: dict[str, Any], raw: dict) -> None:
        kind = str(payload.get("type", ""))
        if kind == "message":
            role = payload.get("role")
            out.event.data = {"role": role, "phase": payload.get("phase")}
            if role == "user":
                out.prompt = _text_content(payload)
        elif kind in {"function_call", "custom_tool_call", "tool_search_call", "web_search_call"}:
            call_id = str(payload.get("call_id") or payload.get("id") or out.event.event_id)
            raw_name = str(payload.get("name") or ("tool_search" if kind == "tool_search_call" else "web_search"))
            server, name = _mcp_parts(raw_name, payload.get("namespace"))
            tool_kind = "mcp" if server else ("custom" if kind == "custom_tool_call" else "function")
            args = _arguments(payload)
            out.tool_call = ToolCall(call_id, out.session.session_id, out.event.timestamp, name, tool_kind, server, "started", arguments=args)
            out.event.data = {"call_id": call_id, "name": name, "kind": tool_kind, "server": server}
        elif kind in {"function_call_output", "custom_tool_call_output", "tool_search_output"}:
            call_id = str(payload.get("call_id") or payload.get("id") or out.event.event_id)
            out.tool_result = {"call_id": call_id, "success": payload.get("status") != "failed", "output": str(payload.get("output", ""))[:512]}
            out.event.data = {"call_id": call_id, "status": payload.get("status")}
        elif kind == "reasoning":
            # Deliberately never retain encrypted or raw reasoning content.
            out.event.data = {"summary_exposed": bool(payload.get("summary"))}
        else:
            self._unsupported(out, raw)

    def _parse_event_msg(self, out: ParsedRecord, payload: dict[str, Any], raw: dict) -> None:
        kind = str(payload.get("type", ""))
        if kind == "user_message":
            out.prompt = _text_content(payload)
            out.event.data = {"has_images": bool(payload.get("images") or payload.get("local_images"))}
        elif kind == "token_count":
            info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
            usage = info.get("total_token_usage") if isinstance(info.get("total_token_usage"), dict) else {}
            out.token_usage = TokenUsage(
                usage.get("input_tokens"), usage.get("cached_input_tokens"),
                usage.get("output_tokens"), usage.get("reasoning_output_tokens"),
                usage.get("total_tokens"), info.get("model_context_window"),
            )
            out.event.data = {"has_usage": bool(usage)}
        elif kind == "item_completed":
            self._parse_completed_item(out, payload.get("item") or {})
        elif kind in {"exec_command_end", "patch_apply_end", "mcp_tool_call_end"}:
            call_id = str(payload.get("call_id") or out.event.event_id)
            duration = _duration_ms(
                payload.get("duration_ms", payload.get("duration")),
                seconds=kind == "mcp_tool_call_end" and "duration_ms" not in payload,
            )
            success = payload.get("success")
            if success is None:
                success = payload.get("exit_code", 0) == 0 and payload.get("status") not in {"failed", "error"}
            out.tool_result = {"call_id": call_id, "success": bool(success), "duration_ms": duration, "output": ""}
            out.event.data = {"call_id": call_id, "success": bool(success), "duration_ms": duration}
            if kind == "patch_apply_end" and isinstance(payload.get("changes"), dict):
                for path, change in payload["changes"].items():
                    change_type = change.get("type", "edit") if isinstance(change, dict) else "edit"
                    action = {"add": "created", "delete": "deleted", "update": "edited"}.get(str(change_type).lower(), "edited")
                    out.file_activity.append((str(path), action, "patch_apply_end"))
        elif kind in {"task_started", "task_complete", "thread_settings_applied", "agent_message", "agent_reasoning", "web_search_end", "thread_rolled_back"}:
            out.event.data = {key: payload.get(key) for key in ("turn_id", "duration_ms", "phase") if key in payload}
        else:
            self._unsupported(out, raw)

    def _parse_completed_item(self, out: ParsedRecord, item: dict[str, Any]) -> None:
        item_type = item.get("type")
        out.event.data = {"item_type": item_type}
        if item_type == "CommandExecution":
            call_id = str(item.get("id") or out.event.event_id)
            command = item.get("command")
            args = {"command": command, "cwd": item.get("cwd")}
            duration = _duration_ms(item.get("duration"), seconds=True)
            out.tool_call = ToolCall(call_id, out.session.session_id, out.event.timestamp, "shell", "shell", status=str(item.get("status")), duration_ms=duration, arguments=args)
            out.tool_result = {"call_id": call_id, "success": item.get("exit_code") == 0, "duration_ms": duration, "output": str(item.get("aggregated_output", ""))[:512]}
        elif item_type == "UserMessage":
            out.prompt = _text_content(item)

    @staticmethod
    def _unsupported(out: ParsedRecord, raw: dict[str, Any]) -> ParsedRecord:
        out.event.unsupported = True
        out.event.data = {}
        out.raw_unknown = raw
        LOG.info("Unsupported Codex event: %s/%s", out.event.category, out.event.subtype)
        return out
