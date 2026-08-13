from __future__ import annotations

from .config import Config
from .database import Database


def settings_summary(config: Config, db: Database) -> dict:
    schema = db.connection.execute(
        "SELECT value FROM metadata WHERE key='schema_version'"
    ).fetchone()
    return {
        "local_only": config.web_host in {"127.0.0.1", "localhost", "::1"},
        "web": {"host": config.web_host, "port": config.web_port, "authentication": False},
        "telemetry": {
            "enabled": config.otel_enabled, "host": config.otel_host, "port": config.otel_port,
            "encodings": ["JSON", "protobuf"],
        },
        "privacy": {
            "prompt_retention": config.log_user_prompts,
            "source_analysis": config.source_analysis_enabled,
            "hidden_reasoning": "Excluded",
        },
        "discovery": {"git_root_detection": config.git_enabled,
                      "scan_interval_seconds": config.scan_interval},
        "database": {"schema_version": int(schema[0]) if schema else None},
        "evidence_note": (
            "This read-only page reports effective Codex Monitor settings and normalized database "
            "metadata. It never displays credentials or modifies configuration."
        ),
    }
