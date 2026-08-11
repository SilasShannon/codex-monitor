from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def discover_session_files(data_roots: Iterable[Path]) -> list[Path]:
    """Discover rollout JSONL files without modifying Codex data roots."""
    found: set[Path] = set()
    for root in data_roots:
        sessions = root.expanduser() / "sessions"
        if not sessions.is_dir():
            continue
        for path in sessions.rglob("rollout-*.jsonl"):
            if path.is_file():
                found.add(path.resolve())
    return sorted(found, key=lambda item: (item.stat().st_mtime_ns, str(item)))
