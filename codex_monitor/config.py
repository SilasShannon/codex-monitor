from __future__ import annotations

import os

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10; installed by the package marker.
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    data_roots: tuple[Path, ...] = field(default_factory=tuple)
    cache_directory: Path = field(
        default_factory=lambda: Path("~/.cache/codex-monitor").expanduser()
    )
    database: Path | None = None
    web_host: str = "127.0.0.1"
    web_port: int = 8787
    cost_enabled: bool = False
    theme: str = "system"
    scan_interval: float = 2.0
    git_enabled: bool = True

    @property
    def database_path(self) -> Path:
        return self.database or self.cache_directory / "monitor.db"


def default_codex_root() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def load_config(path: Path | None = None) -> Config:
    path = path or Path("~/.config/codex-monitor/config.toml").expanduser()
    raw: dict = {}
    if path.is_file():
        if tomllib is None:
            raise RuntimeError("Python 3.10 requires the 'tomli' package to read config.toml")
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    roots = raw.get("data_roots") or [str(default_codex_root())]
    cache = Path(raw.get("cache_directory", "~/.cache/codex-monitor")).expanduser()
    database = raw.get("database")
    return Config(
        data_roots=tuple(Path(item).expanduser() for item in roots),
        cache_directory=cache,
        database=Path(database).expanduser() if database else None,
        web_host=str(raw.get("web_host", "127.0.0.1")),
        web_port=int(raw.get("web_port", 8787)),
        cost_enabled=bool(raw.get("cost_enabled", False)),
        theme=str(raw.get("theme", "system")),
        scan_interval=float(raw.get("scan_interval", 2.0)),
        git_enabled=bool(raw.get("git_enabled", True)),
    )
