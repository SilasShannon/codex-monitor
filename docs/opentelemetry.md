# OpenTelemetry

Codex CLI `0.147.0` supports opt-in OTLP/HTTP or OTLP/gRPC log export, plus
separate trace and metrics exporters. OTel export is disabled by default.

The official Codex documentation lists structured events including
`codex.conversation_starts`, `codex.api_request`, `codex.sse_event`,
`codex.websocket_event`, `codex.user_prompt`, `codex.tool_decision`, and
`codex.tool_result`. Completed response events include token counts. Raw prompt
content remains redacted unless `otel.log_user_prompt` is explicitly enabled.

Codex Monitor currently receives OTLP/HTTP JSON logs at:

```text
http://127.0.0.1:4318/v1/logs
```

Suggested Codex configuration (not written automatically):

```toml
[otel]
environment = "local"
log_user_prompt = false
exporter = { otlp-http = { endpoint = "http://127.0.0.1:4318/v1/logs", protocol = "json" } }
```

Codex configuration must be inspected and backed up before an approved setup
flow merges this block. External forwarding remains opt-in.

## Live verification on Codex CLI 0.147.0

An ephemeral Codex run successfully delivered `codex.conversation_starts`,
`codex.api_request`, `codex.sse_event`, `codex.user_prompt`, WebSocket, startup,
and latency events to the local receiver. Completed response logs used these
exact fields:

- `event.kind = response.completed`
- `input_token_count`
- `cached_token_count`
- `cache_write_token_count`
- `output_token_count`
- `reasoning_token_count`
- `conversation.id`
- `model`

The event stream can contain multiple completed model responses in one Codex
turn, so Codex Monitor deduplicates event identities and aggregates each
completed call. Unneeded `user.email` and `user.account_id` metadata is dropped
before database insertion. The verification used CLI overrides and did not
modify `~/.codex/config.toml`.

Source: [official Codex advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#observability-and-telemetry).
