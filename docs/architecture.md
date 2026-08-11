# Architecture

```text
Codex CLI → read-only rollout JSONL → Codex adapter → normalized records
          → incremental private SQLite cache → queries → terminal + web UI
```

`sources/codex/discovery.py` finds historical rollouts across configurable data
roots. `parser.py` is the sole raw-format adapter. `models/` defines stable
entities. `indexer.py` commits normalized sessions, projects, events, prompts,
tools, results, token snapshots, file activity, and unsupported events.

The UI never parses rollout files and Codex never reads its logs to support the
monitor. SQLite WAL permits dashboard reads during refresh. Milestone 1 uses no
runtime web framework and makes no network requests.

Claude Code Monitor informed local-first UX, project grouping, deduplication,
private-cache handling, background refresh, and web-origin defenses. Its Claude
transcript parser, agents/workflows, billing rules, and directory encoding were
not reused because Codex rollouts have a different event model.
