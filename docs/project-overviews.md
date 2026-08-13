# Project overviews

The Projects page groups Codex sessions using the normalized project association
derived from the Git repository root or working directory. No per-project setup
or modification is required.

Each card summarizes sessions, active sessions, tokens, cache rate, estimated
API-equivalent cost, files touched, test commands, tool activity, models, and
explicit failures. It also builds a short contribution summary from those same
observations—for example, that implementation touched a number of files and
that test commands provide evidence of verification work.

These descriptions deliberately do not claim that a feature is correct,
complete, valuable, or aligned with a business goal. Those conclusions cannot
be established from telemetry alone. Unknown model pricing remains unpriced,
and the card reports how many sessions lack an estimate.

All aggregation is local. Codex session storage and monitored repositories are
read-only inputs, and the project overview does not require prompt logging.
