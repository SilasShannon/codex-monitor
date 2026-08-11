from __future__ import annotations

import os
import time

from .config import Config
from .database import Database
from .indexer import Indexer
from .queries import sessions


def _clear() -> None:
    if os.isatty(1):
        print("\033[2J\033[H", end="")


def render(db: Database) -> str:
    active = [row for row in sessions(db) if row["active"]]
    lines = ["CODEX MONITOR · ACTIVE SESSIONS", ""]
    if not active:
        lines.append("No reliably active Codex sessions detected.")
    for item in active:
        context = "UNKNOWN / NOT EXPOSED"
        if item["context_window"] and item["total_tokens"] is not None:
            context = f"{item['total_tokens']:,} / {item['context_window']:,} tokens"
        lines.extend([
            f"{item['project_name'] or 'Unassigned'} · {item['model'] or 'model unknown'}",
            f"  session {item['session_id']}",
            f"  cwd {item['cwd'] or 'unknown'}",
            f"  context {context}",
            f"  last activity {item['last_activity'] or 'unknown'}",
            "",
        ])
    return "\n".join(lines)


def run(config: Config, db: Database, once: bool = False) -> None:
    indexer = Indexer(config, db)
    try:
        while True:
            indexer.scan()
            _clear()
            print(render(db), flush=True)
            if once:
                return
            time.sleep(config.scan_interval)
    except KeyboardInterrupt:
        return
