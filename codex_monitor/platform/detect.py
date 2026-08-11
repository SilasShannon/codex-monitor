from __future__ import annotations

import os
import platform
from pathlib import Path

from .base import PlatformInfo


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower()
    except OSError:
        return False


def current_platform() -> PlatformInfo:
    system = platform.system().lower()
    home = Path.home()
    if system == "windows":
        config_home = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        cache_home = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    elif system == "darwin":
        config_home = home / "Library" / "Application Support"
        cache_home = home / "Library" / "Caches"
    else:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        cache_home = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
    return PlatformInfo(system, _is_wsl(), home, config_home, cache_home)
