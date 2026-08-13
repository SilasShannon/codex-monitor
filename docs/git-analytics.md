# Git analytics

The Git page summarizes Git commands already present in normalized tool-call
rows. It shows associated projects and sessions, common subcommands, explicit
failures, and whether each subcommand is conventionally read-only or potentially
mutating.

The query inspects the 500 most recent normalized shell/tool calls and displays
up to 50 Git commands. Classification describes command capability, not proof
that repository state changed. Unknown results stay unknown.

This feature never invokes Git and never reads a repository directly. Monitored
repository state remains read-only, and the dashboard continues to consume only
normalized database evidence.
