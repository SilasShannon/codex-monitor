# Web dashboard

`codex-monitor web` serves Overview, Projects, Sessions, and session activity
detail at `http://127.0.0.1:8787`. Data comes from normalized SQLite queries.
HTML text is escaped client-side; query bounds and session IDs are validated.
Host and Origin guards reduce DNS-rebinding and cross-origin risk.

The server has no authentication. Non-loopback binding prints a strong warning.
`--no-network` is accepted and documents the already local-only behavior.
