# Troubleshooting

- No sessions: confirm `~/.codex/sessions` exists or configure `data_roots`.
- Stale index: run `codex-monitor reindex --yes`; raw sessions are untouched.
- Python 3.10 config error: install the package normally so its `tomli`
  compatibility dependency is present.
- Port busy: use `codex-monitor web --port 8788`.
- Unknown metrics: this is intentional when Codex did not expose the value.
