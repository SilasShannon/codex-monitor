# Live monitoring

`codex-monitor` and `codex-monitor live` scan appended bytes every two seconds.
A session is active when its rollout was modified in a recent scan window;
Codex `task_complete` ends a turn, not the resumable session. The view shows model, cwd, activity timestamp,
and context only when both usage and context limit were exposed.

Milestone 1 does not associate processes or claim a current tool. Those require
multi-signal attribution and are deferred rather than guessed.
