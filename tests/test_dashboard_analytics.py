from __future__ import annotations

from datetime import datetime, timezone

from codex_monitor.analytics import usage_breakdown, usage_timeseries


def test_timeseries_and_breakdowns_use_real_session_totals(db) -> None:
    db.connection.execute(
        "INSERT INTO projects VALUES(?,?,?,?)",
        ("project-1", "Monitor", "/work/monitor", "/work/monitor"),
    )
    db.connection.execute(
        """INSERT INTO sessions(
           session_id,source_file,started_at,last_activity,project_key,model,
           input_tokens,cached_input_tokens,cache_write_input_tokens,output_tokens,total_tokens)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        ("session-priced", "otel:session-priced", "2026-08-11T12:00:00Z",
         "2026-08-11T12:10:00Z", "project-1", "gpt-5.6-sol",
         1_000_000, 800_000, 0, 10_000, 1_010_000),
    )
    db.connection.commit()
    series = usage_timeseries(db, 2, datetime(2026, 8, 11, 20, tzinfo=timezone.utc))
    assert series[-1]["total_tokens"] == 1_010_000
    assert series[-1]["estimated_api_equivalent_cost"] == "1.70"
    project = usage_breakdown(db, "project")[0]
    assert project["name"] == "Monitor"
    assert project["cached_input_tokens"] == 800_000
    assert project["estimated_api_equivalent_cost"] == "1.70"
