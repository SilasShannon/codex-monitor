from __future__ import annotations

from pathlib import Path

from codex_monitor.setup import configure_codex_otel


def test_configure_otel_preserves_config_and_creates_backup(tmp_path: Path) -> None:
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text('model = "gpt-test"\n')
    result = configure_codex_otel(config, "http://127.0.0.1:4318/v1/logs")
    assert result.changed
    assert result.backup_path and result.backup_path.read_text() == 'model = "gpt-test"\n'
    updated = config.read_text()
    assert updated.startswith('model = "gpt-test"\n')
    assert "[otel]" in updated
    assert "log_user_prompt = false" in updated
    assert "/v1/metrics" in updated
    assert "/v1/traces" in updated
    assert config.stat().st_mode & 0o777 == 0o600


def test_existing_otel_config_is_never_overwritten(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    original = '[otel]\nexporter = "none"\n'
    config.write_text(original)
    result = configure_codex_otel(config, "http://127.0.0.1:4318/v1/logs")
    assert not result.changed
    assert result.backup_path is None
    assert config.read_text() == original
