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

from .platform import current_platform


@dataclass(frozen=True)
class Config:
    data_roots: tuple[Path, ...] = field(default_factory=tuple)
    cache_directory: Path = field(
        default_factory=lambda: current_platform().monitor_cache
    )
    database: Path | None = None
    web_host: str = "127.0.0.1"
    web_port: int = 8787
    cost_enabled: bool = True
    otel_enabled: bool = True
    otel_host: str = "127.0.0.1"
    otel_port: int = 4318
    log_user_prompts: bool = False
    theme: str = "system"
    scan_interval: float = 2.0
    git_enabled: bool = True
    source_analysis_enabled: bool = False

    @property
    def database_path(self) -> Path:
        return self.database or self.cache_directory / "monitor.db"


def default_codex_root() -> Path:
    return Path(os.environ.get("CODEX_HOME", current_platform().codex_home)).expanduser()


def load_config(path: Path | None = None) -> Config:
    platform_info = current_platform()
    path = path or platform_info.monitor_config
    raw: dict = {}
    if path.is_file():
        if tomllib is None:
            raise RuntimeError("Python 3.10 requires the 'tomli' package to read config.toml")
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    roots = raw.get("data_roots") or [str(default_codex_root())]
    web = raw.get("web", {})
    otel = raw.get("otel", {})
    cost = raw.get("cost", {})
    privacy = raw.get("privacy", {})
    git = raw.get("git", {})
    project_guides = raw.get("project_guides", {})
    history = raw.get("history", {})
    cache = Path(raw.get("cache_directory", platform_info.monitor_cache)).expanduser()
    database = raw.get("database")
    return Config(
        data_roots=tuple(Path(item).expanduser() for item in roots),
        cache_directory=cache,
        database=Path(database).expanduser() if database else None,
        web_host=str(web.get("host", raw.get("web_host", "127.0.0.1"))),
        web_port=int(web.get("port", raw.get("web_port", 8787))),
        cost_enabled=bool(cost.get("enabled", raw.get("cost_enabled", True))),
        otel_enabled=bool(otel.get("enabled", True)),
        otel_host=str(otel.get("host", "127.0.0.1")),
        otel_port=int(otel.get("port", 4318)),
        log_user_prompts=bool(privacy.get("log_user_prompts", False)),
        theme=str(raw.get("theme", "system")),
        scan_interval=float(history.get("scan_interval", raw.get("scan_interval", 2.0))),
        git_enabled=bool(git.get("enabled", raw.get("git_enabled", True))),
        source_analysis_enabled=bool(project_guides.get("source_analysis", False)),
    )
