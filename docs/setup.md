# Setup

Run discovery first:

```bash
codex-monitor setup
```

This detects the platform, Codex executable/home, session directory, monitor
paths, database, local OTel endpoint, and prompt privacy state. Discovery does
not modify Codex configuration.

To configure all three local OTLP/HTTP JSON exporters after reviewing the
detected endpoint:

```bash
codex-monitor setup --configure-otel --yes
```

This refuses to replace existing Codex OTel settings. When it changes an
existing `config.toml`, it first creates a timestamped backup, writes the update
atomically, and applies private file permissions.

After reviewing and explicitly approving the OTel configuration merge, launch:

```bash
codex-monitor web --open
```

The dashboard binds to `127.0.0.1:8787`; the OTel JSON receiver binds to
`127.0.0.1:4318`.
