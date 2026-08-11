# Observed Codex event format

Inspected locally on Codex CLI `0.147.0`; historical files include older
variants. OpenAI documentation does not currently promise this storage schema,
so these are observations, not a public compatibility contract.

Top-level records observed:

- `session_meta`: ID, timestamp, cwd, CLI version, provider, optional Git/context metadata.
- `turn_context`: model, cwd, turn ID, sandbox and collaboration context; a
  summary plus `comp_hash` is recorded as a compaction event without exposing summary text.
- `event_msg`: `user_message`, `token_count`, `item_completed`, `task_started`,
  `task_complete`, `agent_message`, `agent_reasoning`, `exec_command_end`,
  `patch_apply_end`, `mcp_tool_call_end`, `web_search_end`, and settings/rollback events.
- `response_item`: visible messages, function/custom tool calls and outputs,
  tool search, web search, and reasoning containers.
- `world_state`: state marker retained without rendering its full content.

Token snapshots expose input, cached input, output, reasoning output, total, and
sometimes model context window. Missing fields remain unknown. Encrypted/raw
reasoning is explicitly discarded. MCP is detected generically from names such
as `mcp__<server>__<tool>` or namespaces. Unknown records are marked unsupported
and retained only inside the private local cache.
