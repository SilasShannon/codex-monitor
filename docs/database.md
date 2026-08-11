# Database

The default SQLite database is `~/.cache/codex-monitor/monitor.db`. Tables are
`source_files`, `projects`, `sessions`, `events`, `prompts`, `tool_calls`,
`tool_results`, `file_activity`, `token_snapshots`, and `unsupported_events`.

The cache directory is requested as mode `0700` and the database as `0600`.
SQLite WAL supports concurrent refresh and dashboard reads. The schema is
normalized away from Codex's raw representation and versioned in `metadata`.
