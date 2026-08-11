# Codex Monitor

Standalone, system-wide observability for OpenAI Codex. Install it once inside
WSL2 and inspect sessions from any project without changing that project or
feeding its logs back into Codex.

Milestone 1 discovers `~/.codex/sessions/**/rollout-*.jsonl`, incrementally
normalizes records into a private SQLite cache, groups sessions by Git root or
working directory, and provides a terminal monitor plus local web dashboard.

## Install

Python 3.10+ is supported. `pipx` is recommended:

```bash
git clone <your-repository-url> codex-monitor
cd codex-monitor
pipx install .
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
- No telemetry or network feature exists in Milestone 1.
- The web server binds to `127.0.0.1`, has no authentication, validates Host
  and Origin, and warns loudly before non-loopback binding.
- Hidden/encrypted reasoning is not stored or displayed.
- Unsupported raw events stay only in the local monitor cache for future
  parser compatibility.

Token totals are shown only when Codex exposes them. Cost calculation is off;
subscription charge and API-equivalent estimates are intentionally not mixed.

## Configuration

Optional global file: `~/.config/codex-monitor/config.toml`

```toml
data_roots = ["~/.codex"]
cache_directory = "~/.cache/codex-monitor"
web_host = "127.0.0.1"
web_port = 8787
scan_interval = 2.0
git_enabled = true
cost_enabled = false
theme = "system"
```

See [architecture](docs/architecture.md), [event format](docs/codex-event-format.md),
[WSL2](docs/wsl.md), and [privacy/security](docs/privacy-security.md).

## Attribution

The user experience and several design principles were informed by
[Claude Code Monitor](https://github.com/kchernev/claude-code-monitor), MIT ©
Kaloyan Chernev. Codex parsing is a clean adapter for Codex rollout JSONL; it is
not a search-and-replace port. See `NOTICE` and `LICENSE`.
