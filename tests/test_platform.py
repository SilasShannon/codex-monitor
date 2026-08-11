from __future__ import annotations

from pathlib import Path

from codex_monitor.platform import detect


def test_linux_xdg_paths(monkeypatch) -> None:
    monkeypatch.setattr(detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(detect.Path, "home", lambda: Path("/users/tester"))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(detect, "_is_wsl", lambda: False)
    info = detect.current_platform()
    assert info.monitor_config == Path("/users/tester/.config/codex-monitor/config.toml")
    assert info.monitor_database == Path("/users/tester/.cache/codex-monitor/monitor.db")


def test_windows_paths(monkeypatch) -> None:
    monkeypatch.setattr(detect.platform, "system", lambda: "Windows")
    monkeypatch.setattr(detect.Path, "home", lambda: Path("C:/Users/tester"))
    monkeypatch.setenv("APPDATA", "C:/Users/tester/AppData/Roaming")
    monkeypatch.setenv("LOCALAPPDATA", "C:/Users/tester/AppData/Local")
    info = detect.current_platform()
    assert info.monitor_config == Path("C:/Users/tester/AppData/Roaming/codex-monitor/config.toml")
    assert info.monitor_database == Path("C:/Users/tester/AppData/Local/codex-monitor/monitor.db")
