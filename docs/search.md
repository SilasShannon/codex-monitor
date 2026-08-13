# Local evidence search

The Search page queries normalized sessions and projects, retained prompts,
visible assistant updates, tool-call arguments, and file-activity rows. It does
not scan monitored repositories or raw rollout files.

Queries require at least two characters, are capped at 200 characters, and
return at most 20 results. SQL wildcard characters are escaped and treated as
literal input. Prompts can appear only when prompt retention was explicitly
enabled before indexing; hidden or encrypted reasoning is never searchable.
