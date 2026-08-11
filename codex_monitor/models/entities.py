from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    total_tokens: int | None = None
    context_window: int | None = None


@dataclass
class ProjectRecord:
    key: str
    name: str
    working_directory: str
    git_root: str | None = None


@dataclass
class SessionRecord:
    session_id: str
    source_file: str
    started_at: str | None = None
    ended_at: str | None = None
    last_activity: str | None = None
    cwd: str | None = None
    project_key: str | None = None
    model: str | None = None
    cli_version: str | None = None
    title: str | None = None
    active: bool = False
    token_usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass
class ToolCall:
    call_id: str
    session_id: str
    timestamp: str | None
    name: str
    kind: str
    server: str | None = None
    status: str | None = None
    duration_ms: float | None = None
    arguments: dict[str, Any] | None = None


@dataclass
class NormalizedEvent:
    event_id: str
    session_id: str
    timestamp: str | None
    category: str
    subtype: str
    turn_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    unsupported: bool = False
