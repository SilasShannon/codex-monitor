from __future__ import annotations

from dataclasses import replace

from codex_monitor.settings import settings_summary


def test_settings_summary_reports_effective_non_secret_posture(config, db) -> None:
    result = settings_summary(
        replace(config, log_user_prompts=True, source_analysis_enabled=True), db
    )
    assert result["local_only"]
    assert result["privacy"] == {
        "prompt_retention": True, "source_analysis": True, "hidden_reasoning": "Excluded",
    }
    assert result["database"]["schema_version"] == 4
    assert "credentials" in result["evidence_note"]
