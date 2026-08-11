# AGENTS.md

Codex Monitor is an external, local-only observer. Never require changes in a
monitored repository and never modify `~/.codex`, Codex configuration, rollout
files, or Git state.

The dependency direction is strict:

`sources/codex` → normalized `models` → SQLite `database/indexer` → queries → CLI/web.

Raw Codex event handling belongs only in `codex_monitor/sources/codex/`.
Dashboards must consume normalized database rows. Unknown events must not crash
the indexer. Never expose hidden/encrypted reasoning. Do not infer unsupported
token, context, cost, file, process, or activity metrics.

Incremental parsing owns `(path, size, mtime_ns, byte offset, partial tail)` in
`source_files`. Keep Codex input read-only and cache output private. All Git
commands must be read-only. Web defaults to loopback and has no authentication.

Run `PYTHONPATH=. pytest` before committing. Fixtures must be synthetic or
sanitized; never commit real session history.
