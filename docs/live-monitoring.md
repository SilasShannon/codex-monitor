# Live monitoring

`codex-monitor` and `codex-monitor live` scan appended bytes every two seconds.
The dashboard refreshes live summaries every five seconds while refreshing
historical charts once a minute. Explicit Codex task lifecycle events take
priority when determining whether a session is active; recent file or telemetry
activity is used only when no lifecycle event is available.

## Human-readable session briefings

The Live and Sessions pages assemble a deterministic briefing from normalized
evidence. A briefing can show the user's request when prompt logging is enabled,
the latest visible assistant update, observed tools and commands, tests, files,
and short explanations of relevant software-engineering concepts.

Briefings do not use an LLM, send data to a third party, inspect hidden or
encrypted reasoning, or claim an intention that was not observable. Missing
events remain missing; the dashboard labels its evidence boundary instead of
filling gaps with guesses. File changes and command outcomes are shown only when
Codex emitted records that support them.

Milestone 1 does not associate system processes with a session. That requires
multi-signal attribution and is deferred rather than guessed.
