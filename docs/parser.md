# Parser and incremental indexing

Each source row tracks file size, nanosecond mtime, last read byte offset, and
an incomplete trailing line. Appends seek directly to the prior offset. A line
without a newline waits for the next scan. Corrupt complete lines are counted
and skipped. Truncation resets the cursor safely.

Stable hashes over session ID plus canonical record JSON deduplicate repeated
records. Call IDs connect tools and results. Database unique constraints provide
a second idempotency layer. `codex-monitor reindex --yes` deletes and recreates
only the monitor's derived database.
