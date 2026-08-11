# Tool and MCP analytics

The Tools and MCP pages are backed by normalized local Codex events. Tools
shows non-MCP calls such as shell execution, patching, and search when exposed.
MCP groups calls by the server and tool names Codex reported; no server names or
types are hardcoded.

Each view reports calls, explicit successes and failures, unknown outcomes,
average duration when available, sessions, and projects. An absent result is
reported as unknown rather than treated as a failure. Likewise, average duration
is unavailable when neither the call nor its result includes a duration.

Arguments and result previews are not returned by the aggregate endpoints or
rendered on these pages. This keeps the overview useful without unnecessarily
displaying command output or MCP payload data. Monitored repositories and Codex
session files remain read-only inputs.
