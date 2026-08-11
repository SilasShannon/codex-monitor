# Setup

Run discovery first:

```bash
codex-monitor setup
```

This detects the platform, Codex executable/home, session directory, monitor
paths, database, local OTel endpoint, and prompt privacy state. Discovery does
not modify Codex configuration.

After reviewing and explicitly approving the OTel configuration merge, launch:

```bash
codex-monitor web --open
```

The dashboard binds to `127.0.0.1:8787`; the OTel JSON receiver binds to
`127.0.0.1:4318`.
