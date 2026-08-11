# WSL2

Install and run inside Ubuntu under WSL2. The default `~/.codex` resolves to the
Linux user's Codex directory. Working directories under `/home/...` and
`/mnt/c/...` are both grouped from the cwd recorded by Codex; no parent-project
scan is assumed.

Additional Windows or WSL Codex roots can be added to `data_roots` later. Keep
the default web bind at `127.0.0.1`; Windows browsers can normally open that WSL
localhost URL directly.
