from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class OtelSetupResult:
    changed: bool
    config_path: Path
    backup_path: Path | None
    reason: str


def configure_codex_otel(config_path: Path, endpoint: str) -> OtelSetupResult:
    """Append a local OTel block without overwriting any existing OTel settings."""
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Codex Monitor setup only configures a loopback HTTP OTel endpoint")
    existing = config_path.read_text() if config_path.is_file() else ""
    if any(line.strip() == "[otel]" or line.strip().startswith("[otel.")
           for line in existing.splitlines()):
        return OtelSetupResult(False, config_path, None, "Existing Codex OTel configuration preserved")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if config_path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = config_path.with_name(f"{config_path.name}.bak-{stamp}")
        shutil.copy2(config_path, backup)

    separator = "" if not existing or existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    addition = (
        "[otel]\n"
        "environment = \"local\"\n"
        "log_user_prompt = false\n"
        f"exporter = {{ otlp-http = {{ endpoint = \"{endpoint}\", protocol = \"json\" }} }}\n"
        f"metrics_exporter = {{ otlp-http = {{ endpoint = \"{endpoint.removesuffix('/v1/logs')}/v1/metrics\", protocol = \"json\" }} }}\n"
        f"trace_exporter = {{ otlp-http = {{ endpoint = \"{endpoint.removesuffix('/v1/logs')}/v1/traces\", protocol = \"json\" }} }}\n"
    )
    temporary = config_path.with_name(f".{config_path.name}.codex-monitor.tmp")
    temporary.write_text(existing + separator + addition)
    os.chmod(temporary, 0o600)
    os.replace(temporary, config_path)
    return OtelSetupResult(True, config_path, backup, "Local Codex OTel export configured")
