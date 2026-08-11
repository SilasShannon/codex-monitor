# Privacy and security

Session history can contain prompts, paths, commands, outputs, and project
names. Codex Monitor is local-only, has no telemetry, makes no network calls,
and never executes log content. It does not write to Codex data or monitored
repositories. Git discovery uses only `git rev-parse`.

Prompts and unsupported raw records are sensitive and reside in the private
SQLite cache. Reasoning payloads are reduced to a boolean indicating whether an
exposed summary existed; raw and encrypted reasoning are not retained.

The web UI defaults to loopback, rejects untrusted Host and cross-origin
requests, sets restrictive headers, escapes displayed values, and validates
parameters. Binding beyond loopback exposes data without authentication.
