# Troubleshooting

- No sessions: confirm `~/.codex/sessions` exists or configure `data_roots`.
- Stale index: run `codex-monitor reindex --yes`; raw sessions are untouched.
- Python 3.10 config error: install the package normally so its `tomli`
  compatibility dependency is present.
- Unknown metrics: this is intentional when Codex did not expose the value.

## Port already in use

Codex Monitor uses `127.0.0.1:8787` for the dashboard and `127.0.0.1:4318`
for local OpenTelemetry by default. Only one monitor process can own those ports.

If startup says Codex Monitor may already be running, first try opening
<http://127.0.0.1:8787>. Stop an existing foreground server with `Ctrl+C` before
starting another. Another OTLP-compatible service may also own port 4318; change
the configured OTel port only if Codex is updated to export to the same endpoint.

Under WSL, a failed `xdg-open` only means WSL could not find a Linux browser.
Run `codex-monitor web` without `--open` and open the dashboard URL in Windows.
