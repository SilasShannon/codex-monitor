# Architecture

Codex Monitor is a local-first pipeline with two Codex-native inputs:

```text
Codex CLI 0.147+
  ├─ OTLP/HTTP logs, traces, metrics ──> loopback receiver ─┐
  └─ read-only rollout JSONL ──> incremental adapter ──────┤
                                                           v
platform adapters -> normalized records -> versioned SQLite
                                             |
                                  token and cost analytics
                                             |
                                  local JSON API -> web UI
```

OpenTelemetry is the primary live source. Rollout files provide historical
backfill and fields that OTel does not expose. Source-specific assumptions stay
under `codex_monitor/sources/`; analytics never parse raw Codex records.

SQLite stores provenance and deduplicated event identities. Rollout ingestion
tracks path, size, nanosecond mtime, byte offset, and an incomplete trailing
record. Input files and monitored Git repositories are read-only.

The current OTel receiver accepts OTLP/HTTP JSON at `127.0.0.1:4318/v1/logs`.
OTLP protobuf, traces, and metrics are the next receiver increments. The web
server and receiver never bind OTel publicly.

## Verified environment baseline

- WSL2 Ubuntu on ARM64
- Codex CLI `0.147.0`
- Python 3.10 and Node 24
- Codex rollout schema with session metadata, turn context, response items,
  task lifecycle events, tool items, and cumulative token snapshots
- Codex OTel event families documented by OpenAI: conversation starts, API
  requests, SSE/WebSocket events, user prompt metadata, tool decisions/results

See `docs/opentelemetry.md` and `docs/codex-events.md` for evidence and limits.
