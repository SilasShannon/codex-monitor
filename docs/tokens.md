# Token accounting

For a cumulative Codex usage snapshot:

```text
fresh_input = max(input - cached_input - cache_write_input, 0)
processed = input + output
```

Cached reads and cache writes are input subcategories. They are not added to
`input_tokens`. Context-window usage is displayed only when Codex reports both
the current usage and model context limit.

Historical rollout snapshots are cumulative. Session totals therefore use the
latest snapshot rather than summing every snapshot.
