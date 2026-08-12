# Shell learning

The Shell page turns observed `exec_command` and shell tool calls into local,
deterministic learning cards for beginner and intermediate developers.

Each card includes the command Codex exposed, its command category, a concise
purpose description, syntax components, an approximate safety posture, the
observed result, and a learning takeaway. Common programs such as Git, pytest,
ripgrep, npm, Ruff, curl, and Python have curated deterministic explanations.
Unknown programs remain generic rather than receiving a fabricated purpose.

Safety labels are educational hints, not a sandbox or guarantee. A normally
read-only program can still behave differently with unusual flags, scripts, or
inputs. Users should review `--help` and project documentation before manually
reusing unfamiliar commands.

Commands remain local. Environment assignments whose names resemble tokens,
passwords, authentication values, or secrets are redacted before API output.
The explanation describes syntax and common purpose; it does not claim access
to Codex's private intent or hidden reasoning.
