from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .models import ProjectRecord


def _git_root(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    candidate = Path(result.stdout.strip())
    return candidate.resolve() if candidate.is_dir() else None


def identify_project(cwd_text: str | None, git_enabled: bool = True) -> ProjectRecord | None:
    if not cwd_text:
        return None
    cwd = Path(cwd_text).expanduser()
    canonical = cwd.resolve(strict=False)
    root = _git_root(canonical) if git_enabled and canonical.is_dir() else None
    grouping_path = root or canonical
    key = hashlib.sha256(str(grouping_path).encode()).hexdigest()[:20]
    return ProjectRecord(key, grouping_path.name or str(grouping_path), str(canonical), str(root) if root else None)
