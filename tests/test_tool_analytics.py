from __future__ import annotations

from codex_monitor.analytics import tool_analytics
from codex_monitor.cli import main
from codex_monitor.indexer import Indexer


def test_tool_analytics_preserves_unknown_outcomes(config, db) -> None:
    Indexer(config, db).scan()
    result = tool_analytics(db)
    assert result["summary"] == {
        "calls": 1, "successes": 1, "failures": 0, "unknown_outcomes": 0,
        "average_duration_ms": 0, "sessions": 1, "projects": 1,
    }
    assert result["rows"][0]["name"] == "exec_command"
    assert result["rows"][0]["successes"] == 1

    mcp = tool_analytics(db, mcp_only=True)
    assert mcp["summary"]["calls"] == 1
    assert mcp["summary"]["unknown_outcomes"] == 1
    assert mcp["rows"][0]["server"] == "filesystem"
    assert mcp["rows"][0]["name"] == "read_file"
    assert "did not expose" in mcp["evidence_note"]


def test_tool_analytics_counts_failures_and_duration(config, db) -> None:
    Indexer(config, db).scan()
    db.connection.execute(
        "UPDATE tool_results SET success=0,duration_ms=125 WHERE call_id='call-shell'"
    )
    result = tool_analytics(db)
    assert result["summary"]["failures"] == 1
    assert result["summary"]["successes"] == 0
    assert result["summary"]["average_duration_ms"] == 125


def test_tools_and_mcp_cli_commands(config, capsys, tmp_path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(f'data_roots = ["{config.data_roots[0]}"]\n')
    common = ["--config", str(config_path), "--database", str(config.database_path)]
    assert main([*common, "tools"]) == 0
    assert "exec_command" in capsys.readouterr().out
    assert main([*common, "mcp"]) == 0
    output = capsys.readouterr().out
    assert "filesystem" in output and "read_file" in output
