# Codex event fields

The local Codex CLI `0.147.0` rollout files use JSONL records with top-level
families including `session_meta`, `turn_context`, `response_item`,
`event_msg`, and `world_state`.

Observed token snapshots expose cumulative:

- `input_tokens` (inclusive of cached reads and cache writes)
- `cached_input_tokens`
- `cache_write_input_tokens`
- `output_tokens`
- `reasoning_output_tokens`
- `total_tokens`
- `model_context_window`

The observed invariant is `total_tokens = input_tokens + output_tokens`.
Consequently, cached input must not be added to input again during costing.

Encrypted reasoning is never stored. Unsupported records are isolated for
compatibility analysis and do not crash indexing. Product fixtures are
synthetic; real prompts and session contents are never committed.
