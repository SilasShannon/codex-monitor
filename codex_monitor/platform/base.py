from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlatformInfo:
    system: str
    is_wsl: bool
    home: Path
    config_home: Path
    cache_home: Path

    @property
    def codex_home(self) -> Path:
        return self.home / ".codex"

    @property
    def monitor_config(self) -> Path:
        return self.config_home / "codex-monitor" / "config.toml"

    @property
    def monitor_cache(self) -> Path:
        return self.cache_home / "codex-monitor"

    @property
    def monitor_database(self) -> Path:
        return self.monitor_cache / "monitor.db"

    def executable(self, name: str) -> Path | None:
        value = shutil.which(name)
        return Path(value) if value else None
