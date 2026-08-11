# Codex Monitor

Standalone, local-first observability and estimated API-equivalent cost
analytics for OpenAI Codex. Install it once and inspect sessions from every
project without changing monitored repositories or feeding logs back into an
LLM.

Codex Monitor combines an opt-in loopback OpenTelemetry receiver with
incremental historical discovery of `~/.codex/sessions/**/rollout-*.jsonl`.
It normalizes records into a private SQLite cache and powers a React dashboard
with real token, cache, project, session, and deterministic cost data.

## Install

Python 3.10+ is supported. `pipx` is recommended:

```bash
git clone <your-repository-url> codex-monitor
cd codex-monitor
pipx install .
codex-monitor setup
codex-monitor web --open
codex-monitor sessions
```

For development:

```bash
python3 -m pip install -e '.[dev]'
pytest
```

## Commands

```bash
codex-monitor                 # live terminal dashboard
codex-monitor setup           # read-only environment discovery
codex-monitor live
codex-monitor sessions
codex-monitor sessions --search project-name
codex-monitor projects
codex-monitor show <full-session-id>
codex-monitor reindex --yes   # rebuild only the derived monitor database
codex-monitor web --open      # http://127.0.0.1:8787
codex-monitor web --no-network
```

The optional `xmon` alias invokes the same CLI.

## Safety and privacy

- Codex data roots and monitored projects are read-only inputs.
- The cache defaults to `~/.cache/codex-monitor/monitor.db` with private modes.
- OTel ingestion is loopback-only and disabled in Codex until the user opts in;
  external forwarding is never configured automatically.
- The web server binds to `127.0.0.1`, has no authentication, validates Host
  and Origin, and warns loudly before non-loopback binding.
- Hidden/encrypted reasoning is not stored or displayed.
- Unsupported raw events stay only in the local monitor cache for future
  parser compatibility.

Token totals are shown only when Codex exposes them. Subscription charges and
API-equivalent estimates are intentionally not mixed.

## Configuration

Optional global file: `~/.config/codex-monitor/config.toml`

```toml
theme = "system"

[web]
host = "127.0.0.1"
port = 8787

[otel]
enabled = true
host = "127.0.0.1"
port = 4318

[history]
scan_interval = 2.0

[cost]
enabled = true

[privacy]
log_user_prompts = false

[git]
enabled = true
```

Cost values are always labeled **estimated API-equivalent cost**. They are not
actual ChatGPT subscription charges. Unknown model pricing and incomplete token
categories remain unavailable rather than using a guessed fallback.

See [architecture](docs/architecture.md), [OpenTelemetry](docs/opentelemetry.md),
[token accounting](docs/tokens.md), [cost calculations](docs/cost-calculations.md),
[WSL2](docs/wsl.md), and [privacy/security](docs/privacy-security.md).

## Attribution

The user experience and several design principles were informed by
[Claude Code Monitor](https://github.com/kchernev/claude-code-monitor), MIT ©
Kaloyan Chernev. Codex parsing is a clean adapter for Codex rollout JSONL; it is
not a search-and-replace port. See `NOTICE` and `LICENSE`.
