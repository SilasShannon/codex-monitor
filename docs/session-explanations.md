# Session explanations

The Explain page helps a developer understand observable Codex work across
active and recent sessions. It is deterministic and fully local; it does not
call an LLM.

For each session, the page can show:

- an observed phase such as investigating, implementing, debugging, or verifying;
- the latest visible assistant update;
- a plain-language development story assembled from structured activity;
- files and test commands Codex exposed;
- relevant software-engineering concepts;
- useful questions a developer can ask about the work.

The phase is evidence-based. A failed observed test produces `Debugging`, test
activity produces `Verifying`, file activity produces `Implementing`, and other
tool activity produces `Investigating`. When none of those signals exist, the
page says it is waiting for evidence.

This feature does not expose hidden reasoning, reconstruct chain-of-thought, or
infer unobserved intentions. Prompt text appears only when prompt logging has
been explicitly enabled. Paths and commands remain local and are shown only
from normalized events Codex actually emitted.
